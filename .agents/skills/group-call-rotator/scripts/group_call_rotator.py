from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class RuntimeConfig:
    num_groups: int = 1
    students_per_group: int = 1
    absent_students: list[str] | None = None
    excluded_groups: list[str] | None = None
    seed: int | None = None

    def normalized(self) -> "RuntimeConfig":
        return RuntimeConfig(
            num_groups=self.num_groups,
            students_per_group=self.students_per_group,
            absent_students=sorted(set(self.absent_students or [])),
            excluded_groups=sorted({g.upper() for g in (self.excluded_groups or [])}),
            seed=self.seed,
        )


class GroupCallRotatorError(Exception):
    pass


class ValidationError(GroupCallRotatorError):
    pass


class SelectionError(GroupCallRotatorError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError as exc:
        raise ValidationError(f"JSON file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON in file: {path}") from exc

    if not isinstance(data, dict):
        raise ValidationError(f"Expected a JSON object in {path}")
    return data


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def format_history_json(data: dict[str, Any]) -> str:
    """Format history.json with compact horizontal student counts by group."""
    lines: list[str] = ["{"]

    group_counts = data.get("group_call_counts", {})
    group_count_items = sorted(group_counts.items())
    lines.append('  "group_call_counts": {')
    for index, (group_id, count) in enumerate(group_count_items):
        comma = "," if index < len(group_count_items) - 1 else ""
        lines.append(f'    "{group_id}": {count}{comma}')
    lines.append("  },")

    student_counts = data.get("student_call_counts", {})
    student_count_items = sorted(student_counts.items())
    lines.append('  "student_call_counts": {')
    for index, (group_id, members) in enumerate(student_count_items):
        comma = "," if index < len(student_count_items) - 1 else ""
        compact_members = json.dumps(members, ensure_ascii=False, sort_keys=True)
        lines.append(f'    "{group_id}": {compact_members}{comma}')
    lines.append("  },")

    call_log_json = json.dumps(data.get("call_log", []), indent=2, ensure_ascii=False)
    call_log_lines = call_log_json.splitlines()
    if call_log_lines:
        lines.append('  "call_log": ' + call_log_lines[0])
        for line in call_log_lines[1:]:
            lines.append("  " + line)
    else:
        lines.append('  "call_log": []')

    lines.append("}")
    return "\n".join(lines) + "\n"


def save_history_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_history_json(data), encoding="utf-8")


def parse_comma_separated(value: str | None) -> list[str] | None:
    if value is None:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or None


def load_runtime_config(path: Path | None) -> RuntimeConfig:
    if path is None:
        return RuntimeConfig().normalized()

    data = load_json(path)
    config = RuntimeConfig(
        num_groups=int(data.get("num_groups", 1)),
        students_per_group=int(data.get("students_per_group", 1)),
        absent_students=data.get("absent_students"),
        excluded_groups=data.get("excluded_groups"),
        seed=data.get("seed"),
    )
    return config.normalized()


def apply_cli_overrides(config: RuntimeConfig, args: argparse.Namespace) -> RuntimeConfig:
    num_groups = args.num_groups if args.num_groups is not None else config.num_groups
    students_per_group = (
        args.students_per_group
        if args.students_per_group is not None
        else config.students_per_group
    )
    absent_students = (
        parse_comma_separated(args.absent_students)
        if args.absent_students is not None
        else config.absent_students
    )
    excluded_groups = (
        parse_comma_separated(args.excluded_groups)
        if args.excluded_groups is not None
        else config.excluded_groups
    )
    seed = args.seed if args.seed is not None else config.seed

    return RuntimeConfig(
        num_groups=num_groups,
        students_per_group=students_per_group,
        absent_students=absent_students,
        excluded_groups=excluded_groups,
        seed=seed,
    ).normalized()


def validate_runtime_config(config: RuntimeConfig) -> None:
    if config.num_groups <= 0:
        raise ValidationError("num_groups must be a positive integer")
    if config.students_per_group <= 0:
        raise ValidationError("students_per_group must be a positive integer")


def validate_groups_data(data: dict[str, Any]) -> tuple[str, dict[str, list[str]]]:
    class_name = data.get("class_name", "Unnamed Class")
    groups_raw = data.get("groups")

    if not isinstance(groups_raw, list) or not groups_raw:
        raise ValidationError("groups.json must contain a non-empty 'groups' list")

    groups: dict[str, list[str]] = {}
    seen_students: Counter[str] = Counter()

    for entry in groups_raw:
        if not isinstance(entry, dict):
            raise ValidationError("Each group entry must be a JSON object")

        group_id = entry.get("group_id")
        members = entry.get("members")

        if not isinstance(group_id, str) or not group_id.strip():
            raise ValidationError("Each group must have a non-empty string group_id")
        if not isinstance(members, list) or not members:
            raise ValidationError(f"Group {group_id!r} must have a non-empty members list")

        normalized_group_id = group_id.strip().upper()
        if normalized_group_id in groups:
            raise ValidationError(f"Duplicate group_id found: {normalized_group_id}")

        normalized_members: list[str] = []
        for member in members:
            if not isinstance(member, str) or not member.strip():
                raise ValidationError(f"Group {normalized_group_id} contains an invalid member name")
            member_name = member.strip()
            normalized_members.append(member_name)
            seen_students[member_name] += 1

        groups[normalized_group_id] = normalized_members

    duplicates = [name for name, count in seen_students.items() if count > 1]
    if duplicates:
        dup_text = ", ".join(sorted(duplicates))
        raise ValidationError(f"Duplicate student names across groups are not allowed: {dup_text}")

    return class_name, groups


def load_or_initialize_history(path: Path, groups: dict[str, list[str]]) -> dict[str, Any]:
    if not path.exists():
        return {
            "group_call_counts": {group_id: 0 for group_id in groups},
            "student_call_counts": {
                group_id: {student: 0 for student in members}
                for group_id, members in groups.items()
            },
            "call_log": [],
        }

    data = load_json(path)
    group_call_counts = data.get("group_call_counts")
    student_call_counts = data.get("student_call_counts", {})
    call_log = data.get("call_log")

    if not isinstance(group_call_counts, dict):
        raise ValidationError("history.json must contain a 'group_call_counts' object")
    if not isinstance(student_call_counts, dict):
        raise ValidationError("history.json must contain a 'student_call_counts' object")
    if not isinstance(call_log, list):
        raise ValidationError("history.json must contain a 'call_log' list")

    normalized_group_counts: dict[str, int] = {}
    for group_id in groups:
        raw_value = group_call_counts.get(group_id, 0)
        if not isinstance(raw_value, int) or raw_value < 0:
            raise ValidationError(f"Invalid call count for group {group_id}")
        normalized_group_counts[group_id] = raw_value

    normalized_student_counts: dict[str, dict[str, int]] = {}
    for group_id, members in groups.items():
        raw_member_counts = student_call_counts.get(group_id, {})
        if not isinstance(raw_member_counts, dict):
            raise ValidationError(f"Invalid student call counts for group {group_id}")

        normalized_student_counts[group_id] = {}
        for member in members:
            raw_value = raw_member_counts.get(member, 0)
            if not isinstance(raw_value, int) or raw_value < 0:
                raise ValidationError(
                    f"Invalid call count for student {member} in group {group_id}"
                )
            normalized_student_counts[group_id][member] = raw_value

    return {
        "group_call_counts": normalized_group_counts,
        "student_call_counts": normalized_student_counts,
        "call_log": call_log,
    }


def validate_runtime_references(
    config: RuntimeConfig,
    groups: dict[str, list[str]],
) -> None:
    all_students = {student for members in groups.values() for student in members}

    invalid_groups = [group_id for group_id in config.excluded_groups or [] if group_id not in groups]
    if invalid_groups:
        raise ValidationError(
            "Unknown excluded_groups: " + ", ".join(sorted(invalid_groups))
        )

    invalid_students = [student for student in config.absent_students or [] if student not in all_students]
    if invalid_students:
        raise ValidationError(
            "Unknown absent_students: " + ", ".join(sorted(invalid_students))
        )


def build_eligible_members_by_group(
    groups: dict[str, list[str]],
    absent_students: set[str],
    excluded_groups: set[str],
) -> dict[str, list[str]]:
    eligible: dict[str, list[str]] = {}

    for group_id, members in groups.items():
        if group_id in excluded_groups:
            continue
        available_members = [member for member in members if member not in absent_students]
        if available_members:
            eligible[group_id] = available_members

    return eligible


def select_groups(
    num_groups: int,
    eligible_members_by_group: dict[str, list[str]],
    group_call_counts: dict[str, int],
    rng: random.Random,
) -> list[str]:
    if len(eligible_members_by_group) < num_groups:
        available = len(eligible_members_by_group)
        raise SelectionError(
            f"Requested {num_groups} group(s), but only {available} eligible group(s) are available"
        )

    selected: list[str] = []
    working_counts = dict(group_call_counts)
    remaining_groups = set(eligible_members_by_group)

    for _ in range(num_groups):
        min_count = min(working_counts[group_id] for group_id in remaining_groups)
        lowest_groups = [
            group_id for group_id in remaining_groups
            if working_counts[group_id] == min_count
        ]
        chosen_group = rng.choice(sorted(lowest_groups))
        selected.append(chosen_group)
        working_counts[chosen_group] += 1
        remaining_groups.remove(chosen_group)

    return selected


def select_students_for_groups(
    selected_groups: list[str],
    eligible_members_by_group: dict[str, list[str]],
    student_call_counts: dict[str, dict[str, int]],
    students_per_group: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    selections: list[dict[str, Any]] = []

    for group_id in selected_groups:
        available_members = eligible_members_by_group[group_id]
        sample_size = min(students_per_group, len(available_members))

        working_counts = {
            member: student_call_counts.get(group_id, {}).get(member, 0)
            for member in available_members
        }
        remaining_members = set(available_members)
        selected_students: list[str] = []

        for _ in range(sample_size):
            min_count = min(working_counts[member] for member in remaining_members)
            lowest_members = [
                member for member in remaining_members
                if working_counts[member] == min_count
            ]
            chosen_student = rng.choice(sorted(lowest_members))
            selected_students.append(chosen_student)
            working_counts[chosen_student] += 1
            remaining_members.remove(chosen_student)

        selections.append(
            {
                "group_id": group_id,
                "selected_students": selected_students,
                "available_member_count": len(available_members),
            }
        )

    return selections


def update_history(
    history: dict[str, Any],
    selections: list[dict[str, Any]],
    config: RuntimeConfig,
) -> dict[str, Any]:
    group_counts = history["group_call_counts"]
    student_counts = history["student_call_counts"]
    call_log = history["call_log"]

    for item in selections:
        group_id = item["group_id"]
        group_counts[group_id] += 1
        for student in item["selected_students"]:
            student_counts[group_id][student] += 1

    next_round = len(call_log) + 1
    log_entry = {
        "round": next_round,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "selected_groups": [
            {
                "group_id": item["group_id"],
                "selected_students": item["selected_students"],
            }
            for item in selections
        ],
        "excluded_groups": config.excluded_groups or [],
        "absent_students": config.absent_students or [],
        "students_per_group": config.students_per_group,
        "num_groups": config.num_groups,
        "seed": config.seed,
    }
    call_log.append(log_entry)

    return {
        "group_call_counts": group_counts,
        "student_call_counts": student_counts,
        "call_log": call_log,
    }


def build_result(
    class_name: str,
    selections: list[dict[str, Any]],
    config: RuntimeConfig,
    history_path: Path,
    updated_history: dict[str, Any],
) -> dict[str, Any]:
    return {
        "class_name": class_name,
        "selection_summary": {
            "num_groups": config.num_groups,
            "students_per_group": config.students_per_group,
            "selected": selections,
        },
        "runtime_config": {
            "absent_students": config.absent_students or [],
            "excluded_groups": config.excluded_groups or [],
            "seed": config.seed,
        },
        "updated_group_call_counts": updated_history["group_call_counts"],
        "updated_student_call_counts": updated_history["student_call_counts"],
        "history_file": str(history_path),
    }


def format_list(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def format_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{group_id}={count}" for group_id, count in sorted(counts.items()))


def format_human_output(result: dict[str, Any]) -> str:
    selected = result["selection_summary"]["selected"]
    selected_parts = []
    for item in selected:
        students = ", ".join(item["selected_students"])
        selected_parts.append(f"{item['group_id']} -> {students}")

    config = result["runtime_config"]
    summary = result["selection_summary"]

    lines = [
        "Selected this round: " + "; ".join(selected_parts),
        f"Class: {result['class_name']}",
        (
            "Run settings: "
            f"num_groups={summary['num_groups']}, "
            f"students_per_group={summary['students_per_group']}, "
            f"absent_students=[{format_list(config['absent_students'])}], "
            f"excluded_groups=[{format_list(config['excluded_groups'])}], "
            f"seed={config['seed']}"
        ),
        "Updated group call counts: " + format_counts(result["updated_group_call_counts"]),
        f"History saved to: {result['history_file']}",
    ]
    return "\n".join(lines)


def run_rotator(
    groups_path: Path,
    history_path: Path,
    runtime_config_path: Path | None,
    args: argparse.Namespace,
) -> dict[str, Any]:
    config = apply_cli_overrides(load_runtime_config(runtime_config_path), args)
    validate_runtime_config(config)

    groups_data = load_json(groups_path)
    class_name, groups = validate_groups_data(groups_data)
    validate_runtime_references(config, groups)

    history = load_or_initialize_history(history_path, groups)

    rng = random.Random(config.seed)
    absent_students = set(config.absent_students or [])
    excluded_groups = {group_id.upper() for group_id in (config.excluded_groups or [])}

    eligible_members_by_group = build_eligible_members_by_group(
        groups=groups,
        absent_students=absent_students,
        excluded_groups=excluded_groups,
    )

    if not eligible_members_by_group:
        raise SelectionError("No eligible groups are available after applying exclusions and absences")

    selected_groups = select_groups(
        num_groups=config.num_groups,
        eligible_members_by_group=eligible_members_by_group,
        group_call_counts=history["group_call_counts"],
        rng=rng,
    )

    selections = select_students_for_groups(
        selected_groups=selected_groups,
        eligible_members_by_group=eligible_members_by_group,
        student_call_counts=history["student_call_counts"],
        students_per_group=config.students_per_group,
        rng=rng,
    )

    updated_history = update_history(history, selections, config)
    save_history_json(history_path, updated_history)

    return build_result(
        class_name=class_name,
        selections=selections,
        config=config,
        history_path=history_path,
        updated_history=updated_history,
    )


def get_skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_asset_path(filename: str) -> Path:
    return get_skill_root() / "assets" / filename


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Select classroom groups fairly using rotation, exclusions, and history tracking."
    )
    parser.add_argument(
        "--groups",
        default=str(default_asset_path("groups.json")),
        help="Path to groups.json. Defaults to assets/groups.json inside the skill folder.",
    )
    parser.add_argument(
        "--history",
        default=str(default_asset_path("history.json")),
        help="Path to history.json. Defaults to assets/history.json and will be initialized automatically if missing.",
    )
    parser.add_argument(
        "--config",
        help="Optional path to a runtime_config.json file.",
    )
    parser.add_argument("--num-groups", type=int, help="Override num_groups")
    parser.add_argument(
        "--students-per-group",
        type=int,
        help="Override students_per_group",
    )
    parser.add_argument(
        "--absent-students",
        help="Comma-separated absent student names, e.g. 'Ben,Peter'",
    )
    parser.add_argument(
        "--excluded-groups",
        help="Comma-separated excluded group IDs, e.g. 'G2,G5'",
    )
    parser.add_argument("--seed", type=int, help="Optional random seed for reproducible output")
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Print the full JSON result instead of the compact human-readable summary.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        result = run_rotator(
            groups_path=Path(args.groups),
            history_path=Path(args.history),
            runtime_config_path=Path(args.config) if args.config else None,
            args=args,
        )
    except GroupCallRotatorError as exc:
        print(f"Error: {exc}")
        return 1

    if args.json_output:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_human_output(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


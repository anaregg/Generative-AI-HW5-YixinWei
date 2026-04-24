---
name: group-call-rotator
description: Fairly selects classroom discussion groups and students using cumulative call history, absent student handling, and excluded group rules. Use when the user asks to choose groups or students for class participation, cold calling, discussion rotation, or classroom Q&A in a grouped course.
---

# Group Call Rotator

## Purpose

This skill helps an instructor or teaching assistant fairly select classroom groups and students for participation. It is designed for classes where students are already divided into groups and the instructor wants to avoid repeatedly calling on the same group or the same student.

The skill uses a Python script to perform the deterministic part of the workflow: reading the group roster, checking absences and exclusions, applying rotation rules, selecting groups and students, and updating persistent history.

## When to use this skill

Use this skill when the user wants to:

- Randomly but fairly select one or more classroom groups.
- Select one or more students from selected groups.
- Avoid calling on excluded groups for the current round.
- Exclude absent students from selection.
- Maintain call history across class sessions.
- Demonstrate a reusable classroom participation workflow with deterministic script support.

Example user requests:

- "Select one group and one student for today's discussion."
- "Call on two groups, but exclude G3 because they are presenting."
- "Ben and Emma are absent today. Pick one group and one student."
- "Use the classroom group rotator to choose students fairly."

## When not to use this skill

Do not use this skill when the user asks for:

- General classroom management advice.
- Creating lesson plans or discussion questions.
- Grading student answers.
- Evaluating student performance.
- Selecting students without a group roster.
- A completely manual choice with no fairness or rotation requirement.
- A selection that intentionally ignores the rotation logic, unless the user clearly understands it is no longer a fair rotation.

If the user asks to force-select from a specific group or student, explain that this bypasses the normal fair rotation logic. Only proceed if the user confirms that they want to override the fairness rule.

## Required file

The skill expects a group roster file:

```text
assets/groups.json
```

The expected format is:

```json
{
  "class_name": "INFOTECH-101",
  "groups": [
    {
      "group_id": "G1",
      "members": ["Alice", "Ben", "Cathy", "Daniel", "Emma"]
    },
    {
      "group_id": "G2",
      "members": ["Frank", "Grace", "Henry", "Ivy", "Jack", "Kelly"]
    }
  ]
}
```

Rules for `groups.json`:

- Each group must have a unique `group_id`.
- Each group must have a non-empty `members` list.
- Student names should not be duplicated across groups.
- Group IDs are normalized to uppercase by the script.

## Optional history file

The script uses this file by default:

```text
assets/history.json
```

This file is optional before the first run.

If `assets/history.json` does not exist, the script automatically creates it after the first selection.

The history file stores:

- Cumulative group call counts.
- Cumulative student call counts within each group.
- A round-by-round call log.

## Runtime parameters

The user may provide these optional parameters through natural language or command-line arguments:

| Parameter | Meaning | Default |
|---|---|---|
| `num_groups` | Number of groups to select | `1` |
| `students_per_group` | Number of students to select from each selected group | `1` |
| `absent_students` | Students who should not be selected this round | empty |
| `excluded_groups` | Groups that should not be selected this round | empty |
| `seed` | Optional random seed for reproducible output | none |
| `json_output` | Whether to print full JSON instead of compact text | false |

Use defaults when the user omits optional values.

Ask a follow-up question only if the request is ambiguous or impossible to execute safely, such as when no group roster exists or when the user references a group/student that cannot be identified.

## Selection rules

The script applies two levels of fairness.

### Group-level selection

1. Start with all groups in `groups.json`.
2. Remove groups listed in `excluded_groups`.
3. Remove any group that has no available students after applying `absent_students`.
4. Among remaining groups, select from the groups with the lowest cumulative group call count.
5. If multiple groups are tied for the lowest count, select randomly among them.
6. If multiple groups are requested, repeat the process without selecting the same group twice in the same run.

### Student-level selection

1. For each selected group, remove absent students.
2. Among available students in that group, select from the students with the lowest cumulative individual call count.
3. If multiple students are tied for the lowest count, select randomly among them.
4. Update the selected students' call counts after selection.

## How to run the script

The script is located at:

```text
scripts/group_call_rotator.py
```

From the skill folder, run:

```bash
python scripts/group_call_rotator.py
```

From the repository root, run:

```bash
python .agents/skills/group-call-rotator/scripts/group_call_rotator.py
```

The script automatically uses:

```text
assets/groups.json
assets/history.json
```

unless custom paths are provided.

## Example commands

Select one group and one student using default settings:

```bash
python scripts/group_call_rotator.py
```

Select two groups, one student per group, excluding G2 and G5:

```bash
python scripts/group_call_rotator.py --num-groups 2 --students-per-group 1 --excluded-groups G2,G5
```

Select one group while excluding absent students:

```bash
python scripts/group_call_rotator.py --absent-students Ben,Peter
```

Use a seed for reproducible demo output:

```bash
python scripts/group_call_rotator.py --seed 42
```

Print full JSON output:

```bash
python scripts/group_call_rotator.py --json-output
```

## Expected compact output

The default output is human-readable and starts with the selected group and student:

```text
Selected this round: G4 -> Victor; G6 -> Daisy
Class: INFOTECH-101
Run settings: num_groups=2, students_per_group=1, absent_students=[Ben, Peter], excluded_groups=[G2, G5], seed=42
Updated group call counts: G1=1, G2=0, G3=1, G4=1, G5=0, G6=1
History saved to: assets/history.json
```

## Expected JSON output

When `--json-output` is used, the script returns a structured JSON result containing:

- `class_name`
- selected groups and students
- runtime configuration
- updated group call counts
- updated student call counts
- history file path

Use this mode when the user wants a structured result or when debugging the selection process.

## Error handling

If the script returns an error, explain the issue clearly and do not invent a result.

Common errors include:

- Missing `assets/groups.json`
- Invalid JSON format
- Unknown group in `excluded_groups`
- Unknown student in `absent_students`
- Too few eligible groups available
- All students in eligible groups are absent

If the error is caused by missing or ambiguous user input, ask the user for the missing information.

## Limitations

- This skill does not grade or evaluate students.
- This skill does not create or modify the group roster automatically.
- This skill assumes the group roster is already prepared in `groups.json`.
- The fairness logic is based on cumulative call counts, not student ability, participation quality, or learning needs.
- If the user manually excludes many groups, the result may be fair only within the remaining eligible groups.
- The random selection is pseudo-random and can be made reproducible with a seed.

## Agent instructions

When this skill is relevant:

1. Read this `SKILL.md`.
2. Confirm that `assets/groups.json` exists or ask the user to provide a roster.
3. Convert the user's natural-language request into runtime parameters.
4. Use defaults for omitted optional parameters.
5. Run `scripts/group_call_rotator.py`.
6. Present the selected group(s) and student(s) first.
7. Briefly explain any exclusions, absences, or fairness constraints applied.
8. Mention that the history file was updated.
9. Do not bypass the fairness rules unless the user explicitly requests an override.
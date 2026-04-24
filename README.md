# HW5: Group Call Rotator Skill

## Project Overview

This project builds a reusable AI skill called `group-call-rotator`.

The skill is designed for classroom discussion settings where students are already divided into groups. Instead of randomly calling on the same group repeatedly, the skill uses a Python script to fairly select groups and students based on cumulative call history.

The script supports:

- Fair group rotation based on cumulative group call counts
- Fair student selection within each group based on individual call counts
- Excluding absent students
- Excluding specific groups for the current round
- Persistent history tracking across runs
- Compact human-readable output and optional JSON output

## Why I Chose This Skill

I chose this skill because classroom cold-calling is a narrow but realistic workflow where pure randomness can feel unfair.

A plain AI prompt could randomly choose a group or student, but it would not reliably maintain history, apply exclusion rules, validate input, or update future selection counts. The Python script is therefore load-bearing: it handles the deterministic parts of the workflow, while the agent interprets the user request and presents the result clearly.

This makes the skill more than a one-time prompt. It becomes a reusable classroom participation tool.

## Skill Location

```text
.agents/
└─ skills/
   └─ group-call-rotator/
      ├─ SKILL.md
      ├─ assets/
      │  ├─ groups.json
      │  └─ history.json
      └─ scripts/
         └─ group_call_rotator.py
```

## What the Skill Does

The `group-call-rotator` skill helps select classroom discussion groups and students fairly.

It uses two levels of fairness:

1. **Group-level fairness**  
   The script selects from groups with the lowest cumulative call count.

2. **Student-level fairness**  
   Within the selected group, the script selects from students with the lowest individual call count.

If multiple groups or students are tied, the script uses pseudo-random selection among the tied candidates.

## Input Files

### `assets/groups.json`

This file contains the class roster and group assignments.

Example:

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

### `assets/history.json`

This file stores selection history.

It is optional before the first run. If it does not exist, the script automatically creates it.

The history file tracks:

- Group call counts
- Student call counts
- Round-by-round selection logs

## How to Run

From the repository root:

```bash
python .agents/skills/group-call-rotator/scripts/group_call_rotator.py
```

The script automatically uses:

```text
.agents/skills/group-call-rotator/assets/groups.json
.agents/skills/group-call-rotator/assets/history.json
```

## Example Commands

Select one group and one student using default settings:

```bash
python .agents/skills/group-call-rotator/scripts/group_call_rotator.py
```

Select two groups and one student per group:

```bash
python .agents/skills/group-call-rotator/scripts/group_call_rotator.py --num-groups 2 --students-per-group 1
```

Exclude specific groups:

```bash
python .agents/skills/group-call-rotator/scripts/group_call_rotator.py --excluded-groups G2,G5
```

Exclude absent students:

```bash
python .agents/skills/group-call-rotator/scripts/group_call_rotator.py --absent-students Ben,Peter
```

Use a seed for reproducible output:

```bash
python .agents/skills/group-call-rotator/scripts/group_call_rotator.py --seed 42
```

Print full JSON output:

```bash
python .agents/skills/group-call-rotator/scripts/group_call_rotator.py --json-output
```

## Example Output

Default compact output:

```text
Selected this round: G3 -> Peter
Class: INFOTECH-101
Run settings: num_groups=1, students_per_group=1, absent_students=[none], excluded_groups=[none], seed=None
Updated group call counts: G1=1, G2=1, G3=1, G4=1, G5=0, G6=1
History saved to: assets/history.json
```

## Demo Prompts Tested in Codex

### 1. Normal Case

Prompt:

```text
Use Group Call Rotator to select one group and one student for today's discussion. Use the default roster and update the history file.
```

Result:

```text
Selected for today: G3 -> Peter.
```

Codex used the default roster, applied the fair rotation logic, selected one group and one student, and updated `history.json`.

### 2. Edge Case

Prompt:

```text
Use Group Call Rotator to select two groups and one student per group. Exclude G1, G2, G3, G4, and G5 for this round.
```

Result:

```text
Requested 2 group(s), but only 1 eligible group(s) are available.
```

This demonstrated that the script validates whether enough eligible groups remain after exclusions. No history update was made because the run failed.

### 3. Cautious / Limited Case

Prompt:

```text
Use Group Call Rotator, but only select from G2. Explain whether this still follows the normal fair rotation rule.
```

Result:

```text
Selecting only from G2 would not follow the normal fair group-rotation rule.
```

Codex correctly explained that forcing a specific group bypasses the normal group-level fairness rule. Student selection within G2 could still be fair, but the group selection would be manually constrained.

## What the Python Script Does

The Python script performs the deterministic part of the workflow:

1. Loads the group roster from `groups.json`
2. Loads or initializes `history.json`
3. Validates runtime parameters
4. Removes excluded groups
5. Removes absent students
6. Selects groups with the lowest cumulative group call count
7. Selects students with the lowest individual call count within each selected group
8. Updates group and student call counts
9. Writes the updated history file
10. Prints a compact summary or full JSON output

This deterministic logic is why the script is central to the skill.

## What Worked Well

The skill worked well in Codex because:

- Codex discovered the skill from `.agents/skills/group-call-rotator/SKILL.md`
- The skill description clearly matched classroom group selection requests
- The script handled fairness rules and validation reliably
- The output was easy to read in the terminal
- The history file made the workflow reusable across multiple class sessions

## Limitations

This skill has several limitations:

- It assumes the group roster is already prepared in `groups.json`
- It does not automatically create or edit group assignments
- It does not evaluate student performance
- It does not consider student ability, participation quality, or learning needs
- Fairness is based only on cumulative call counts
- If the user excludes many groups, fairness only applies within the remaining eligible groups
- Random selection is pseudo-random, though it can be made reproducible with a seed

## Video Link

Add walkthrough video link here:

```text
https://youtu.be/YQ02zb4Pb1c
```
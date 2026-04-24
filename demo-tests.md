# Skill Test Cases

This document records the three required test cases for the `group-call-rotator` skill.

The skill was tested in Codex after it was discovered through the workspace skills list.

## Test 1: Normal Case

### Prompt

```text
Use Group Call Rotator to select one group and one student for today's discussion. Use the default roster and update the history file.
```

### Result

```text
Selected for today: G3 -> Peter.
```

### Notes

Codex used the default roster in `groups.json` with the skill's default settings:

- `num_groups=1`
- `students_per_group=1`
- no absent students
- no excluded groups

The skill selected one group and one student using the fair rotation logic and updated `history.json`.

## Test 2: Edge Case

### Prompt

```text
Use Group Call Rotator to select two groups and one student per group. Exclude G1, G2, G3, G4, and G5 for this round.
```

### Result

```text
Requested 2 group(s), but only 1 eligible group(s) are available.
```

### Notes

This tested the case where the user requested more groups than were available after exclusions.

The skill correctly returned an error instead of inventing a result. No history update was made because the run failed.

## Test 3: Cautious / Limited Case

### Prompt

```text
Use Group Call Rotator, but only select from G2. Explain whether this still follows the normal fair rotation rule.
```

### Result

```text
Selecting only from G2 would not follow the normal fair group-rotation rule.
```

### Notes

This tested a constrained request that would bypass the normal group-level fairness rule.

Codex correctly explained that forcing a specific group is a manual override. Student selection within G2 could still be fair, but the group selection itself would no longer follow the normal fair rotation logic.
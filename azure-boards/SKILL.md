---
name: azure-boards
description: >-
  Manage Azure Boards work items via Azure CLI (az boards). Covers creating,
  updating, deleting, linking, and querying tasks, bugs, user stories, and
  other work item types. Use when the user asks to create tickets, manage
  sprints, link work items, update Azure DevOps boards, or any Azure Boards
  operations.
---

# Azure Boards CLI Reference

## Prerequisites

- **Azure CLI** with the `azure-devops` extension installed.
- Authenticated via `az login`.
- Defaults configured (optional but recommended):

```bash
az devops configure -d organization=https://dev.azure.com/ORG
az devops configure -d project=PROJECT_NAME
```

Verify setup:

```bash
az devops configure -l
az version  # check "azure-devops" under extensions
```

---

## Create Work Item

```bash
az boards work-item create \
  --type "Task" \
  --title "My Task" \
  --description "Description here" \
  --iteration "ProjectName\Sprint 1" \
  --area "ProjectName\TeamName" \
  --assigned-to "user@example.com" \
  --fields "Microsoft.VSTS.Scheduling.OriginalEstimate=2" \
  -o json
```

### Key Arguments

| Arg             | Required | Notes                                                   |
| --------------- | -------- | ------------------------------------------------------- |
| `--type`        | Yes      | `Task`, `Bug`, `User Story`, `Issue`, `Epic`, `Feature` |
| `--title`       | Yes      | Title of the work item                                  |
| `--description` | No       | HTML or plain text                                      |
| `--iteration`   | No       | Full iteration path: `Project\Sprint N`                 |
| `--area`        | No       | Full area path: `Project\Area`                          |
| `--assigned-to` | No       | Display name or email                                   |
| `--fields`      | No       | Space-separated `"field=value"` pairs                   |
| `--discussion`  | No       | Adds a comment                                          |
| `--reason`      | No       | Reason for the state                                    |

### Common Fields (`--fields`)

| Field                                        | Purpose           | Example              |
| -------------------------------------------- | ----------------- | -------------------- |
| `Microsoft.VSTS.Scheduling.OriginalEstimate` | Estimate in hours | `0.5` = 30 min       |
| `Microsoft.VSTS.Scheduling.RemainingWork`    | Remaining hours   | `4`                  |
| `Microsoft.VSTS.Scheduling.CompletedWork`    | Completed hours   | `2`                  |
| `Microsoft.VSTS.Common.Priority`             | Priority (1-4)    | `1` = critical       |
| `Microsoft.VSTS.Common.Severity`             | Bug severity      | `2 - High`           |
| `System.Tags`                                | Tags              | `"frontend; urgent"` |
| `System.State`                               | State             | `Active`, `Closed`   |

> **NOTE:** `--parent` is NOT a valid argument on `az boards work-item create`. You must create the item first, then add a parent relation separately.

---

## Link Work Items (Parent/Child)

```bash
az boards work-item relation add \
  --id CHILD_ID \
  --relation-type parent \
  --target-id PARENT_ID \
  -o json
```

### Relation Types

| Type          | Meaning                            |
| ------------- | ---------------------------------- |
| `parent`      | Target is the parent of `--id`     |
| `child`       | Target is a child of `--id`        |
| `related`     | General related link               |
| `predecessor` | Target must complete before `--id` |
| `successor`   | `--id` must complete before target |

Multiple targets: `--target-id 100,101,102`

You can also use `--target-url` for cross-project links.

### List Available Relation Types

```bash
az boards work-item relation list-type -o table
```

---

## Update Work Item

```bash
az boards work-item update \
  --id 12345 \
  --state "Active" \
  --assigned-to "user@example.com" \
  --fields "Microsoft.VSTS.Scheduling.RemainingWork=2" \
  -o json
```

---

## Delete Work Item

```bash
# Soft delete (moves to recycle bin)
az boards work-item delete --id 12345 --yes -o json

# Permanent delete
az boards work-item delete --id 12345 --destroy --yes -o json
```

---

## Show / Query Work Items

```bash
# Show single item
az boards work-item show --id 12345 -o json

# Show with relations
az boards work-item relation show --id 12345 -o json

# Query using WIQL
az boards query --wiql "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.IterationPath] = 'Project\Sprint 1' AND [System.WorkItemType] = 'Task'" -o table
```

---

## Typical Workflow: Create Task Under User Story

This is the most common pattern — two commands, sequential:

```bash
# 1. Create the task
az boards work-item create \
  --type "Task" \
  --title "Implement feature X" \
  --description "Details here" \
  --iteration "MyProject\Sprint 5" \
  --fields "Microsoft.VSTS.Scheduling.OriginalEstimate=4" \
  -o json

# 2. Link to parent user story (use the ID from step 1 output)
az boards work-item relation add \
  --id NEW_TASK_ID \
  --relation-type parent \
  --target-id PARENT_STORY_ID \
  -o json
```

---

## Iteration / Sprint Management

```bash
# List iterations for a team
az boards iteration team list --team "MyTeam" -o table

# Show iteration details
az boards iteration team show --team "MyTeam" --id ITERATION_ID -o json
```

---

## Gotchas

- **No `--parent` flag on create** — always use `relation add` as a second step.
- **Backslash in iteration paths** — use single backslash in shell: `"Project\Sprint 1"`.
- **Estimate fields are in hours** — `0.5` = 30 minutes, `8` = one day.
- **Work item types are case-sensitive** — `"User Story"` not `"user story"`.
- **`--fields` uses full API field names** — find them via `az boards work-item show` on an existing item.
- **`--yes` flag** — required on delete to skip interactive confirmation prompt.

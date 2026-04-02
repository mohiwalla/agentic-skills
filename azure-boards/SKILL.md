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

## Required Rules

- Use the project name defined in `AGENTS.md` for all Azure Boards commands and paths.
- If the project name is missing in `AGENTS.md`, ask the user explicitly and do not assume a project name.
- For "assigned to me" lookups or assigning tickets to the user, use the value from `AZURE_DEVOPS_USERNAME`.
- When creating new tickets, always assign them to the latest iteration by default.
- Only use a non-latest iteration when the user explicitly asks for a different one.

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
| `--description` | No       | **Must be HTML** — markdown is NOT rendered (see below) |
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

## CRITICAL: Description field requires HTML, NOT markdown

The `--description` flag on `az boards work-item create` and `az boards work-item update`
is rendered by Azure DevOps as **HTML**. If you pass raw markdown (`## Heading`, `- [ ] item`,
`` `code` ``), it will be displayed as **literal plain text** — no headings, no lists, no formatting.

**Always use HTML tags in the description:**

```html
<h2>Summary</h2>
<p>Explanation of the issue with <code>inline code</code> and <b>bold</b>.</p>

<h2>Steps to reproduce</h2>
<ol>
  <li>First step.</li>
  <li>Second step.</li>
</ol>

<h2>Affected endpoints</h2>
<ul>
  <li><code>GET /api/v1/example</code></li>
</ul>

<h2>Acceptance criteria</h2>
<ul>
  <li>Endpoint returns <b>200</b> for valid input.</li>
</ul>

<h2>Definition of done</h2>
<ul>
  <li>Root cause fixed.</li>
  <li>E2E test passes.</li>
</ul>
```

**Quick mapping:**

| Markdown              | HTML equivalent                          |
| --------------------- | ---------------------------------------- |
| `## Heading`          | `<h2>Heading</h2>`                       |
| `**bold**`            | `<b>bold</b>`                            |
| `` `code` ``          | `<code>code</code>`                      |
| `- item`              | `<ul><li>item</li></ul>`                 |
| `1. item`             | `<ol><li>item</li></ol>`                 |
| `- [ ] checkbox`      | `<ul><li>checkbox text</li></ul>`        |
| paragraph break       | `<p>text</p>` or `<br>`                  |

**Do NOT:**
- Pass raw markdown to `--description` — it will render as a single blob of text.
- Repeat the work item title inside Description (it's already in `System.Title`).
- Add a `**Description:**` label inside the Description field (it's redundant).

**The `--discussion` flag** (comments) also accepts HTML, same rules apply.

---

## Gotchas

- **Description is HTML, not markdown** — see section above. This is the #1 mistake.
- **No `--parent` flag on create** — always use `relation add` as a second step.
- **Backslash in iteration paths** — use single backslash in shell: `"Project\Sprint 1"`.
- **Estimate fields are in hours** — `0.5` = 30 minutes, `8` = one day.
- **Work item types are case-sensitive** — `"User Story"` not `"user story"`.
- **`--fields` uses full API field names** — find them via `az boards work-item show` on an existing item.
- **`--yes` flag** — required on delete to skip interactive confirmation prompt.
- **Sprint board visibility** — tickets won't appear on a sprint taskboard if unassigned and the board is filtered by person. Always set `--assigned-to`.

---
name: azure-boards
description: >-
  Manage Azure Boards work items directly with Azure CLI (`az boards`).
  Covers creating, updating, deleting, linking, querying tasks, bugs,
  user stories, and other work item types. Use when the user asks to
  create tickets, manage sprints, link work items, update Azure DevOps
  boards, or any Azure Boards operations.
---

# Azure Boards CLI Reference

## Required Rules

- Use the project name defined in `AGENTS.md` for all Azure Boards commands and paths.
- If the project name is missing in `AGENTS.md`, ask the user explicitly and do not assume a project name.
- For "assigned to me" lookups or assigning tickets to the user, use the value from `AZURE_DEVOPS_USERNAME`.
- When creating new tickets, always assign them to the latest iteration by default.
- Only use a non-latest iteration when the user explicitly asks for a different one.

## Configuration

Required environment variable:

- `AZURE_DEVOPS_USERNAME` — used for "assigned to me" lookups and assignments to the current user.

Rules:

- Assume `az` CLI and `azure-devops` extension are already installed and authenticated.
- Assume Azure DevOps defaults (`organization`, `project`) are already configured in the environment.
- If defaults are missing at runtime, ask the user for the missing value(s) and continue with explicit `--org` / `--project` flags.

## Execution Model

Use Azure CLI commands via `az boards`.

---

## Create Work Item

```bash
az boards work-item create \
  --type "Task" \
  --title "My Task" \
  --description "<p>HTML description here</p>" \
  --assigned-to "user@example.com" \
  --fields "System.IterationPath=Project\\Sprint 1" "Microsoft.VSTS.Scheduling.OriginalEstimate=2" \
  --tags "frontend;urgent"
```

### Key Arguments

| Arg             | Required | Notes                                                                                                                          |
| --------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `--type`        | Yes      | `Task`, `Bug`, `User Story`, `Issue`, `Epic`, `Feature`                                                                        |
| `--title`       | Yes      | Title of the work item                                                                                                         |
| `--description` | No       | **Must be HTML** — markdown is NOT rendered (see below)                                                                        |
| `--assigned-to` | No       | Display name or email                                                                                                          |
| `--area`        | No       | Full area path via field: `System.AreaPath=Project\\Area`                                                                      |
| `--iteration`   | No       | If using this flag in your CLI version, set full path `Project\\Sprint 1`; otherwise set `System.IterationPath` via `--fields` |
| `--state`       | No       | e.g. `New`, `Active`, `Closed`                                                                                                 |
| `--reason`      | No       | Reason for the state                                                                                                           |
| `--tags`        | No       | Semicolon-separated tags                                                                                                       |
| `--fields`      | No       | Space-separated `Key=Value` pairs for any field                                                                                |

### Common Fields (`--fields`)

| Field                                        | Purpose           | Example        |
| -------------------------------------------- | ----------------- | -------------- |
| `Microsoft.VSTS.Scheduling.OriginalEstimate` | Estimate in hours | `0.5` = 30 min |
| `Microsoft.VSTS.Scheduling.RemainingWork`    | Remaining hours   | `4`            |
| `Microsoft.VSTS.Scheduling.CompletedWork`    | Completed hours   | `2`            |
| `Microsoft.VSTS.Common.Priority`             | Priority (1-4)    | `1` = critical |
| `Microsoft.VSTS.Common.Severity`             | Bug severity      | `2 - High`     |

---

## Update Work Item

```bash
az boards work-item update \
  --id 12345 \
  --state "Active" \
  --assigned-to "user@example.com" \
  --fields "Microsoft.VSTS.Scheduling.RemainingWork=2"
```

All arguments are optional except `--id`. Only provided fields are updated.

---

## Get / Show Work Item

```bash
az boards work-item show --id 12345
```

Returns work item JSON including core fields and links.

---

## Delete Work Item

```bash
# Soft delete (recycle bin)
az boards work-item delete --id 12345 --yes

# Permanent delete
az boards work-item delete --id 12345 --yes --destroy
```

---

## Query Work Items (WIQL)

```bash
az boards query \
  --wiql "SELECT [System.Id] FROM WorkItems WHERE [System.IterationPath] = 'Project\Sprint 1' AND [System.WorkItemType] = 'Task'" \
  --top 50 \
  --output json
```

If you need full details for each result, fetch each returned ID with `az boards work-item show --id <id>`.

```bash
az boards query \
  --wiql "SELECT [System.Id] FROM WorkItems WHERE [System.AssignedTo] = 'Kamaljot Singh' AND [System.State] = 'Active'" \
  --output json
```

---

## Link Work Items (Relations)

```bash
az boards work-item relation add \
  --id 100 \
  --relation-type Parent \
  --target-id 200
```

### Relation Types

| Type          | Meaning                            |
| ------------- | ---------------------------------- |
| `Parent`      | Target is the parent of `--id`     |
| `Child`       | Target is a child of `--id`        |
| `Related`     | General related link               |
| `Predecessor` | Target must complete before `--id` |
| `Successor`   | `--id` must complete before target |

Remove a relation by relation ID:

```bash
az boards work-item relation remove \
  --id 100 \
  --relation-id 300
```

---

## Comments (Discussion)

```bash
# Add a comment
az boards work-item update \
  --id 12345 \
  --discussion "<p>Investigation complete — root cause is X.</p>"
```

---

## Iteration / Sprint Management

```bash
# List all iterations
az boards iteration project list

# Filter by timeframe
az boards iteration team list --timeframe current

# Show the current (or latest) iteration
az boards iteration team list --timeframe current --output table
```

---

## Typical Workflow: Create Task Under User Story

Two-step workflow with direct CLI:

```bash
az boards work-item create \
  --type "Task" \
  --title "Implement feature X" \
  --description "<p>Details here</p>" \
  --assigned-to "user@example.com" \
  --fields "Microsoft.VSTS.Scheduling.OriginalEstimate=4"

az boards work-item relation add \
  --id <new-task-id> \
  --relation-type Parent \
  --target-id 5678
```

---

## CRITICAL: Description and comment fields require HTML, NOT markdown

The `--description` and `--discussion` (comment) fields are rendered by Azure DevOps as **HTML**.
If you pass raw markdown, it displays as literal plain text.

**Always use HTML tags:**

```html
<h2>Summary</h2>
<p>Explanation with <code>inline code</code> and <b>bold</b>.</p>

<h2>Steps to reproduce</h2>
<ol>
  <li>First step.</li>
  <li>Second step.</li>
</ol>

<h2>Acceptance criteria</h2>
<ul>
  <li>Endpoint returns <b>200</b> for valid input.</li>
</ul>
```

**Quick mapping:**

| Markdown        | HTML equivalent          |
| --------------- | ------------------------ |
| `## Heading`    | `<h2>Heading</h2>`       |
| `**bold**`      | `<b>bold</b>`            |
| `` `code` ``    | `<code>code</code>`      |
| `- item`        | `<ul><li>item</li></ul>` |
| `1. item`       | `<ol><li>item</li></ol>` |
| paragraph break | `<p>text</p>` or `<br>`  |

**Do NOT:**

- Pass raw markdown to `--description` — it will render as a single blob of text.
- Repeat the work item title inside Description (it's already in `System.Title`).
- Add a `**Description:**` label inside the Description field (it's redundant).

---

## Gotchas

- **Description is HTML, not markdown** — see section above. This is the #1 mistake.
- **Parent link is a separate step** — create the work item first, then link parent/child with `relation add`.
- **Set iteration explicitly when creating** — use `System.IterationPath` in `--fields` (latest/current iteration by default unless user asks otherwise).
- **Estimate fields are in hours** — `0.5` = 30 minutes, `8` = one day.
- **Work item types are case-sensitive** — `"User Story"` not `"user story"`.
- **`--fields` uses full API field names** — find them via `show` on an existing item.
- **Sprint board visibility** — tickets won't appear on a sprint taskboard if unassigned and the board is filtered by person. Always set `--assigned-to`.

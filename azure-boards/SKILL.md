---
name: azure-boards
description: >-
  Manage Azure Boards work items via a Python helper (REST API wrapper).
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

Required environment variables:

- `AZURE_DEVOPS_ORG` — organization name (e.g. `sifars`)
- `AZURE_DEVOPS_PROJECT` — project name (e.g. `Ipns-opad`)
- `AZURE_DEVOPS_PAT` — personal access token

Rules:

- Prefer env vars; do not hard-code PATs in files.
- If any required config is missing, ask the user before executing commands.

## Execution Model

Use the Python helper instead of raw `az boards` CLI commands:

`python3 ~/.cursor/skills/azure-boards/scripts/azure_boards_api.py <subcommand> [args...]`

This provides consistent JSON output, automatic retry on transient errors, auto-detection of the current iteration, and a `--parent-id` flag on create (no separate link step needed).

---

## Create Work Item

```bash
python3 ~/.cursor/skills/azure-boards/scripts/azure_boards_api.py create \
  --type "Task" \
  --title "My Task" \
  --description "<p>HTML description here</p>" \
  --assigned-to "user@example.com" \
  --parent-id 12345 \
  --field "Microsoft.VSTS.Scheduling.OriginalEstimate=2" \
  --tags "frontend; urgent"
```

### Key Arguments

| Arg             | Required | Notes                                                          |
| --------------- | -------- | -------------------------------------------------------------- |
| `--type`        | Yes      | `Task`, `Bug`, `User Story`, `Issue`, `Epic`, `Feature`        |
| `--title`       | Yes      | Title of the work item                                         |
| `--description` | No       | **Must be HTML** — markdown is NOT rendered (see below)        |
| `--iteration`   | No       | Full path: `Project\Sprint 1` (auto-detects if omitted)        |
| `--area`        | No       | Full area path e.g. `Project\Area`                             |
| `--assigned-to` | No       | Display name or email                                          |
| `--state`       | No       | e.g. `New`, `Active`, `Closed`                                 |
| `--reason`      | No       | Reason for the state                                           |
| `--tags`        | No       | Semicolon-separated tags                                       |
| `--field`       | No       | Repeatable `"Key=Value"` for any field                         |
| `--parent-id`   | No       | Parent work item ID — auto-creates the parent link             |

### Common Fields (`--field`)

| Field                                        | Purpose           | Example              |
| -------------------------------------------- | ----------------- | -------------------- |
| `Microsoft.VSTS.Scheduling.OriginalEstimate` | Estimate in hours | `0.5` = 30 min       |
| `Microsoft.VSTS.Scheduling.RemainingWork`    | Remaining hours   | `4`                  |
| `Microsoft.VSTS.Scheduling.CompletedWork`    | Completed hours   | `2`                  |
| `Microsoft.VSTS.Common.Priority`             | Priority (1-4)    | `1` = critical       |
| `Microsoft.VSTS.Common.Severity`             | Bug severity      | `2 - High`           |

---

## Update Work Item

```bash
python3 ~/.cursor/skills/azure-boards/scripts/azure_boards_api.py update \
  --id 12345 \
  --state "Active" \
  --assigned-to "user@example.com" \
  --field "Microsoft.VSTS.Scheduling.RemainingWork=2"
```

All arguments are optional except `--id`. Only provided fields are updated.

---

## Get / Show Work Item

```bash
python3 ~/.cursor/skills/azure-boards/scripts/azure_boards_api.py get --id 12345
```

Returns a summarized JSON with id, type, title, state, assigned_to, iteration, area, tags, priority, parent, url, and relations.

---

## Delete Work Item

```bash
# Soft delete (recycle bin)
python3 ~/.cursor/skills/azure-boards/scripts/azure_boards_api.py delete --id 12345

# Permanent delete
python3 ~/.cursor/skills/azure-boards/scripts/azure_boards_api.py delete --id 12345 --destroy true
```

---

## Query Work Items (WIQL)

```bash
python3 ~/.cursor/skills/azure-boards/scripts/azure_boards_api.py query \
  --wiql "SELECT [System.Id] FROM WorkItems WHERE [System.IterationPath] = 'Project\Sprint 1' AND [System.WorkItemType] = 'Task'" \
  --top 50
```

Returns hydrated work items (not just IDs). Use `--fields` to request only specific fields:

```bash
python3 ~/.cursor/skills/azure-boards/scripts/azure_boards_api.py query \
  --wiql "SELECT [System.Id] FROM WorkItems WHERE [System.AssignedTo] = 'Kamaljot Singh' AND [System.State] = 'Active'" \
  --fields "System.Title,System.State,System.IterationPath"
```

---

## Link Work Items (Relations)

```bash
python3 ~/.cursor/skills/azure-boards/scripts/azure_boards_api.py relation-add \
  --id 100 \
  --relation-type parent \
  --target-id 200
```

### Relation Types

| Type          | Meaning                            |
| ------------- | ---------------------------------- |
| `parent`      | Target is the parent of `--id`     |
| `child`       | Target is a child of `--id`        |
| `related`     | General related link               |
| `predecessor` | Target must complete before `--id` |
| `successor`   | `--id` must complete before target |

Remove a relation by its index (from the `get` output):

```bash
python3 ~/.cursor/skills/azure-boards/scripts/azure_boards_api.py relation-remove \
  --id 100 \
  --relation-index 0
```

---

## Comments (Discussion)

```bash
# Add a comment
python3 ~/.cursor/skills/azure-boards/scripts/azure_boards_api.py comment-add \
  --id 12345 \
  --text "<p>Investigation complete — root cause is X.</p>"

# List comments
python3 ~/.cursor/skills/azure-boards/scripts/azure_boards_api.py comment-list --id 12345 --top 10
```

---

## Iteration / Sprint Management

```bash
# List all iterations
python3 ~/.cursor/skills/azure-boards/scripts/azure_boards_api.py iterations

# Filter by timeframe
python3 ~/.cursor/skills/azure-boards/scripts/azure_boards_api.py iterations --timeframe current

# Show the current (or latest) iteration
python3 ~/.cursor/skills/azure-boards/scripts/azure_boards_api.py current-iteration
```

---

## Typical Workflow: Create Task Under User Story

Single command — `--parent-id` handles the link automatically:

```bash
python3 ~/.cursor/skills/azure-boards/scripts/azure_boards_api.py create \
  --type "Task" \
  --title "Implement feature X" \
  --description "<p>Details here</p>" \
  --parent-id 5678 \
  --assigned-to "user@example.com" \
  --field "Microsoft.VSTS.Scheduling.OriginalEstimate=4"
```

---

## CRITICAL: Description and comment fields require HTML, NOT markdown

The `--description` and `--text` (comment) fields are rendered by Azure DevOps as **HTML**.
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

| Markdown              | HTML equivalent                          |
| --------------------- | ---------------------------------------- |
| `## Heading`          | `<h2>Heading</h2>`                       |
| `**bold**`            | `<b>bold</b>`                            |
| `` `code` ``          | `<code>code</code>`                      |
| `- item`              | `<ul><li>item</li></ul>`                 |
| `1. item`             | `<ol><li>item</li></ol>`                 |
| paragraph break       | `<p>text</p>` or `<br>`                  |

**Do NOT:**

- Pass raw markdown to `--description` — it will render as a single blob of text.
- Repeat the work item title inside Description (it's already in `System.Title`).
- Add a `**Description:**` label inside the Description field (it's redundant).

---

## Gotchas

- **Description is HTML, not markdown** — see section above. This is the #1 mistake.
- **`--parent-id` on create** handles the link in one step (no separate `relation-add` needed).
- **Iteration auto-detection** — if `--iteration` is omitted on `create`, the script auto-detects the current sprint.
- **Estimate fields are in hours** — `0.5` = 30 minutes, `8` = one day.
- **Work item types are case-sensitive** — `"User Story"` not `"user story"`.
- **`--field` uses full API field names** — find them via `get` on an existing item.
- **Sprint board visibility** — tickets won't appear on a sprint taskboard if unassigned and the board is filtered by person. Always set `--assigned-to`.

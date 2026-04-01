---
name: clockify
description: >-
  Manage Clockify via a Python helper with common operations: start/stop timers,
  list/get/update/delete time entries, and reporting queries. Use when the user
  mentions Clockify, time tracking, timers, time entries, or reports.
---

# Clockify

## Configuration

Required:

- `CLOCKIFY_API_KEY` (environment variable)
- `CLOCKIFY_WORKSPACE_ID` (environment variable or derive from `AGENTS.md`)
- `CLOCKIFY_USER_ID` (environment variable or derive from `AGENTS.md`)

Optional:

- `CLOCKIFY_PROJECT_ID` (environment variable or derive from `AGENTS.md`)

Rules:

- Prefer secrets in env vars; do not store API keys in files.
- If `clockify_workspace_id` / `clockify_user_id` / `clockify_project_id` are expected from `AGENTS.md` but missing, ask the user explicitly and do not assume values.
- If any required Clockify config is missing, ask the user before executing commands.

## Preferred Project IDs

Use these canonical project mappings when selecting `--project-id`:

- `interviews` -> `684159afaefffc1d755dad58`
- `bank-statement-scrubber` -> `68257b3da1956c686d2dde07`
- `ipns-opad` -> `67f5206630556a37a1373ef0`
- `ipns-scorify-and-sowrite` -> `6826df4c537d26222f921adc`
- `preston-estate-planning` -> `689c69c9f06cda4f1f5bac9e`
- `fusionbills` -> `6683f524cb1ffd40a77c2404`
- `learning` -> `6065c6616467674f50aab2b0`
- `weekly-call` -> `684698050300f917a039dc8a`

If no clear project match exists, ask the user before starting the timer.

## Execution Model

Use the Python helper instead of ad-hoc curl calls:

`python3 ~/.cursor/skills/clockify/scripts/clockify_api.py <subcommand> [args...]`

This gives a better DX and consistent JSON output.

## Common Operations

Start timer:

```bash
python3 ~/.cursor/skills/clockify/scripts/clockify_api.py start \
  --description "fix/<ticket-number>: <ticket-title>" \
  --project-id "<clockify-project-id>" \
  --tag "AI"
```

Stop timer:

```bash
python3 ~/.cursor/skills/clockify/scripts/clockify_api.py stop
```

List entries:

```bash
python3 ~/.cursor/skills/clockify/scripts/clockify_api.py list \
  --start "2026-04-01T00:00:00Z" \
  --end "2026-04-02T00:00:00Z" \
  --description "fix/<ticket-number>"
```

List only in-progress entries:

```bash
python3 ~/.cursor/skills/clockify/scripts/clockify_api.py list --in-progress true
```

Get one entry:

```bash
python3 ~/.cursor/skills/clockify/scripts/clockify_api.py get --id "<time-entry-id>"
```

Update an entry:

```bash
python3 ~/.cursor/skills/clockify/scripts/clockify_api.py update \
  --id "<time-entry-id>" \
  --start "2026-04-02T10:00:00Z" \
  --end "2026-04-02T11:30:00Z" \
  --description "fix/<ticket-number>: updated details" \
  --tag "AI" \
  --billable true
```

List tags:

```bash
python3 ~/.cursor/skills/clockify/scripts/clockify_api.py list-tags --name "AI"
```

Create a tag:

```bash
python3 ~/.cursor/skills/clockify/scripts/clockify_api.py create-tag --name "AI"
```

Notes:

- `start` and `update` both support repeatable `--tag "<name>"` and `--tag-id "<id>"`.
- Use `--create-missing-tags true` with `start` or `update` to create missing tag names on demand.

Delete an entry:

```bash
python3 ~/.cursor/skills/clockify/scripts/clockify_api.py delete --id "<time-entry-id>"
```

Workspace in-progress snapshot:

```bash
python3 ~/.cursor/skills/clockify/scripts/clockify_api.py in-progress
```

## Reporting Notes

For most practical reporting, use `list` with:

- `--start` and `--end` for date range windows
- `--description` for ticket filtering
- `--page` and `--page-size` for pagination

If the user needs advanced analytics aggregation, pull entries first and then summarize in a follow-up step.

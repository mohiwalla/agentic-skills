---
name: azure-ticket-execution
description: >-
  Execute Azure DevOps ticket workflows with strict branch naming, semantic
  commit messages, and pull request conventions. Use when implementing issue
  fixes tied to ticket numbers or when the user asks for commit/PR discipline.
---

# Azure Ticket Execution

## Required Rules

- Use the project name defined in `AGENTS.md` in all ticket URLs, Azure paths, and command values.
- If the project name is missing in `AGENTS.md`, ask the user explicitly and do not assume a project name.
- For "assigned to me" lookups or assigning tickets to the user, use the value from `AZURE_DEVOPS_USERNAME`.
- When creating new tickets, always place them in the latest iteration by default.
- Only use a different iteration when the user explicitly requests it.
- Always start by creating an easy-to-skim execution plan and ask the user to confirm before proceeding.
- This planning-and-confirmation step is mandatory even when plan mode is not explicitly selected.
- Do not `git commit`, `git push`, or raise a PR unless the user explicitly asks for that step or clearly approves it.
- After the plan is approved, implement all required changes end-to-end.
- Always switch to `develop` first, pull the latest changes, and create a new working branch from updated `develop`.
- Add corresponding tests in the same repository when tests or testing infrastructure already exist.
- After code changes, run formatting, linting, and a lint-fix pass at least once.
- Resolve all lint errors and warnings introduced by the change.
- For TypeScript codebases, build the project and fix all resulting errors and warnings before completion.
- When raising a PR, always ask the user for required reviewer name(s) if not already provided.
- Always add required reviewers: the user (`AZURE_DEVOPS_USERNAME`) and any reviewer(s) requested by the user.
- When creating a PR, always link the relevant Azure DevOps work item ID(s) to the PR using `--work-items` in `az repos pr create`.
- Always link the originating Azure DevOps work item to the branch and commits by including `AB#<ticket-number>` in the first commit message on that branch.
- Always target PRs to `develop` unless the user explicitly asks for a different target branch.
- When a ticket reference is received and work begins, automatically start a Clockify timer using the `clockify` skill with ticket number/title in the description.
- When a PR is successfully created, automatically stop the running Clockify timer using the `clockify` skill.

## Commit Convention

Semantic commit messages: `label(scope): description`

Labels: `fix`, `feat`, `chore`, `docs`, `test`, `devops`

### Git and PR commands (by phase)

Each block is separate on purpose: **only run a block after the user has explicitly approved that phase.** Do not chain commit → push → PR in one shot unless the user approved all of them.

**Phase A — branch from `develop` (after plan approval, before local edits)**

```bash
git checkout develop
git pull origin develop
git checkout -b fix/<ticket-number>
```

**Phase B — commit (only after user explicitly approves committing)**

```bash
git add <changed-files>
git commit -m "$(cat <<'EOF'
fix: handle SOCKS proxy authentication

Fixes AB#<ticket-number>
EOF
)"
```

**Phase C — push (only after user explicitly approves pushing)**

```bash
git push origin fix/<ticket-number>
```

**Phase D — open PR (only after user explicitly approves opening a PR)**

```bash
az repos pr create \
  --source-branch fix/<ticket-number> \
  --target-branch develop \
  --work-items <ticket-number> \
  --title "fix: handle SOCKS proxy authentication" \
  --description "$(cat <<'EOF'
## Summary
- <describe the change very! briefly>

Fixes AB#<ticket-number>
EOF
)"
```

Never add Co-Authored-By agents in commit message.
Branch naming for issue fixes: `fix/ticket-number>`

## Clockify Integration

Use the `clockify` skill for all Clockify operations (start, stop, list, edit, reports).
This skill auto-triggers timer start on ticket-work start and timer stop after successful PR creation.

## Azure Boards Integration

Use the `azure-boards` skill's Python helper for all work-item operations (create, update, get, query, comment, link).
See the `azure-boards` skill for the full HTML mapping reference, examples, and command syntax.

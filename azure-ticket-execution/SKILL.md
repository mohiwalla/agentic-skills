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
- When creating new tickets, always place them in the latest iteration by default.
- Only use a different iteration when the user explicitly requests it.
- Always start by creating an easy-to-skim execution plan and ask the user to confirm before proceeding.
- This planning-and-confirmation step is mandatory even when plan mode is not explicitly selected.
- After the plan is approved, implement all required changes end-to-end.
- Always switch to `develop` first, pull the latest changes, and create a new working branch from updated `develop`.
- Add corresponding tests in the same repository when tests or testing infrastructure already exist.
- After code changes, run formatting, linting, and a lint-fix pass at least once.
- Resolve all lint errors and warnings introduced by the change.
- For TypeScript codebases, build the project and fix all resulting errors and warnings before completion.

## Commit Convention

Semantic commit messages: `label(scope): description`

Labels: `fix`, `feat`, `chore`, `docs`, `test`, `devops`

```bash
git checkout -b fix-16486
# ... make changes ...
git add <changed-files>
git commit -m "$(cat <<'EOF'
fix(proxy): handle SOCKS proxy authentication

Fixes: https://dev.azure.com/sifars/<project-name>/_workitems/edit/16486
EOF
)"
git push origin fix-16486
az repos pr create \
  --source-branch fix-16486 \
  --target-branch main \
  --title "fix(proxy): handle SOCKS proxy authentication" \
  --description "$(cat <<'EOF'
## Summary
- <describe the change very! briefly>

Fixes https://dev.azure.com/sifars/<project-name>/_workitems/edit/16486
EOF
)"
```

Never add Co-Authored-By agents in commit message.
Branch naming for issue fixes: `fix-<ticket-number>`

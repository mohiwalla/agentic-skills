---
name: azure-ticket-execution
description: >-
    Execute Azure DevOps ticket workflows with strict branch naming, semantic
    commit messages, and pull request conventions. Use when implementing issue
    fixes tied to ticket numbers or when the user asks for commit/PR discipline.
---

# Azure Ticket Execution

## Commit Convention

Semantic commit messages: `label(scope): description`

Labels: `fix`, `feat`, `chore`, `docs`, `test`, `devops`

```bash
git checkout -b fix-16486
# ... make changes ...
git add <changed-files>
git commit -m "$(cat <<'EOF'
fix(proxy): handle SOCKS proxy authentication

Fixes: https://dev.azure.com/sifars/Ipns-opad/_workitems/edit/16486
EOF
)"
git push origin fix-16486
gh pr create --repo microsoft/playwright --head username:fix-16486 \
  --title "fix(proxy): handle SOCKS proxy authentication" \
  --body "$(cat <<'EOF'
## Summary
- <describe the change very! briefly>

Fixes https://dev.azure.com/sifars/Ipns-opad/_workitems/edit/16486
EOF
)"
```

Never add Co-Authored-By agents in commit message.
Branch naming for issue fixes: `fix-<issue-number>`

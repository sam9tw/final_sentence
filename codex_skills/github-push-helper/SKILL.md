---
name: github-push-helper
description: Use when the user wants to commit and push the current project to GitHub, update an existing GitHub repository, publish local changes, or avoid repeating the same git push workflow. This skill handles checking git status, staging intended changes, creating a non-interactive commit, verifying remotes and branch tracking, and pushing safely.
---

# GitHub Push Helper

Use this skill when the user asks to:

- push the current project to GitHub
- upload recent changes
- commit and push
- sync the current branch to `origin`
- repeat the same GitHub publishing workflow as before

## Workflow

1. Inspect the repository state first:
   Run `git status --short`, `git remote -v`, and `git branch -vv`.

2. Confirm the repository is initialized:
   If `.git` is missing, run `git init` and configure `user.name` / `user.email` only if needed.

3. Review what will be published:
   Summarize staged and unstaged changes briefly before committing.

4. Stage the intended project changes:
   Prefer `git add -A` when the user asked to publish the current project state.
   Do not revert unrelated user changes.

5. Create a normal commit:
   Use a concise non-interactive commit message.
   Do not amend unless the user explicitly asks.

6. Verify remote setup:
   If `origin` is missing, ask the user for the repository URL or create the remote if they already provided it.

7. Push safely:
   Push the current branch to `origin`.
   If credentials or sandbox restrictions block the push, retry with escalation and preserve the existing branch history.

8. Report the result:
   Share the remote URL, branch, latest commit hash, and whether the working tree is clean.

## Guardrails

- Never use `git reset --hard`, `git checkout --`, or interactive git flows unless the user explicitly asks.
- Never remove or overwrite unrelated user work.
- If the repository has no remote and the user has not provided one, pause and ask for the GitHub URL.
- If there are merge conflicts or non-fast-forward push errors, stop and explain the state before taking further action.
- If the push succeeds only after adding `safe.directory`, mention that clearly in the final summary.

## Typical Commands

```powershell
git status --short
git remote -v
git branch -vv
git add -A
git commit -m "Your commit message"
git push
```

# rhicnlorg fork of pr-agent

This repository is a fork of [`The-PR-Agent/pr-agent`](https://github.com/The-PR-Agent/pr-agent). We use pr-agent as a CLI pull request reviewer on our T3 hosts. This file lists every change that we keep on top of upstream, so that an update to a new upstream version is a checklist and not a search.

## Rules for work on the fork

1. Never open a pull request or push to `The-PR-Agent/pr-agent`. Open pull requests only with `gh pr create --repo rhicnlorg/pr-agent`. In a local clone, the `upstream` remote has its push URL set to `DISABLED`, and `gh repo set-default` is `rhicnlorg/pr-agent`.
2. Keep each change small and in its own commit (or a few commits), on top of the upstream base. Do not mix a fork change with an upstream fix.
3. Do not change upstream files when a new file can do the same work. A new file never causes a conflict during an update.
4. A new behaviour is off by default. With the new setting empty, pr-agent must work as upstream.
5. Add or update the row in [Changes](#changes) in the same commit as the change.

## Upstream base

| Item | Value |
| --- | --- |
| Upstream repository | `https://github.com/The-PR-Agent/pr-agent` |
| Upstream base | `0d241cc1` on `main` (`v0.49.0-236-g0d241cc1`), 2026-11-07 |
| Fork release tag | none yet. Format: `v<upstream version>-rhicnlorg.<n>`, for example `v0.49.0-rhicnlorg.1` |

## Changes

| ID | Change | Why | Files | How to check | Upstream status |
| --- | --- | --- | --- | --- | --- |
| FK-1 | Fork notes: this file and the fork notice at the top of `AGENTS.md` | Tell agents and maintainers about the fork | `FORK.md`, `AGENTS.md` (first lines) | Read the files | Fork only |
| FK-2 | `pr_reviewer.reviewer_id`: one persistent review comment per reviewer. Pattern `[a-z0-9][a-z0-9-]{0,39}`. Set it with `--pr_reviewer.reviewer_id=<id>` or `PR_REVIEWER__REVIEWER_ID`. Empty works as upstream | Run several reviewers (for example `thermo`, `ui`, `security`) on one pull request. Upstream uses one fixed marker, `<!-- pr-agent:review:full -->`, so each review replaces the last | `pr_agent/algo/comment_identity.py`, `pr_agent/tools/pr_reviewer.py`, `pr_agent/settings/configuration.toml`, `docs/docs/usage-guide/configuration_reference.md` (generated), `tests/unittest/test_reviewer_id.py`, `tests/unittest/test_config_comment_overrides.py`, `tests/unittest/test_config_reference.py` (key count) | `PYTHONPATH=. uv run pytest tests/unittest/test_reviewer_id.py tests/unittest/test_review_comment_identity.py tests/unittest/test_hidden_comment_markers.py tests/unittest/test_pr_reviewer_finding_state.py tests/unittest/test_config_reference.py tests/unittest/test_config_comment_overrides.py -q` | Fork only. Not offered |

## How to update to a new upstream version

1. `git fetch upstream --tags`.
2. Rebase the fork commits onto the new upstream tag or commit.
3. For each row in [Changes](#changes): resolve conflicts in the listed files, then run its check.
4. Remove the row of a change that upstream now has, and drop its commit.
5. Update [Upstream base](#upstream-base), and tag the result with the next fork release tag.

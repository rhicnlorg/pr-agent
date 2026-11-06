"""rhicnlorg fork (FORK.md, FK-2): one persistent review comment per reviewer id."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from dynaconf import Dynaconf

import pr_agent.algo.comment_identity as comment_identity
from pr_agent.algo.comment_identity import (
    PRReviewHeader,
    PRReviewIdentity,
    add_comment_identity,
    comment_carries_other_identity,
    configured_reviewer_id,
    get_pr_review_comment_identifiers,
    hidden_marker_forms,
    legacy_pr_review_header,
    pr_review_identity,
    render_hidden_marker,
)
from pr_agent.algo.utils import update_settings_from_args
from pr_agent.config_loader import current_dir, dynconf_kwargs, get_settings
from pr_agent.git_providers.bitbucket_provider import BitbucketProvider
from pr_agent.git_providers.git_provider import GitProvider
from tests.unittest._settings_helpers import restore_settings, snapshot_settings


@pytest.fixture
def reviewer_id():
    snapshot = snapshot_settings(["pr_reviewer.reviewer_id"])

    def set_reviewer_id(value):
        get_settings().set("pr_reviewer.reviewer_id", value)

    yield set_reviewer_id
    restore_settings(snapshot)


def _review_comment(identity, provider, heading="## PR Reviewer Guide 🔍"):
    return SimpleNamespace(body=add_comment_identity(f"{heading}\n\nold", identity, provider))


def _publish(provider, comments):
    provider.get_issue_comments = MagicMock(return_value=comments)
    provider.get_issue_comments_newest_first = MagicMock(return_value=list(reversed(comments)))
    provider.edit_comment = MagicMock(return_value=True)
    provider.publish_comment = MagicMock()
    provider.get_latest_commit_url = MagicMock(return_value="https://example.com/commit/123")
    provider.get_comment_url = MagicMock(return_value="https://example.com/comment/1")
    return GitProvider.publish_persistent_comment_full(
        provider,
        "## PR Reviewer Guide 🔍\n\nnew",
        initial_header="## PR Reviewer Guide 🔍",
        identity_marker=pr_review_identity(),
        legacy_initial_header=legacy_pr_review_header(),
        final_update_message=False,
    )


@pytest.mark.parametrize("value", ["", "  ", None])
def test_without_reviewer_id_the_identity_is_the_upstream_identity(reviewer_id, value):
    reviewer_id(value)

    assert configured_reviewer_id() == ""
    assert pr_review_identity() == PRReviewIdentity.REGULAR.value
    assert pr_review_identity(incremental=True) == PRReviewIdentity.INCREMENTAL.value
    assert legacy_pr_review_header() == f"{PRReviewHeader.REGULAR.value} 🔍"
    assert get_pr_review_comment_identifiers(full=True, incremental=True) == (
        PRReviewIdentity.REGULAR.value,
        PRReviewHeader.REGULAR.value,
        PRReviewIdentity.INCREMENTAL.value,
        PRReviewHeader.INCREMENTAL.value,
    )


def test_reviewer_id_gives_its_own_markers_and_no_legacy_heading(reviewer_id):
    reviewer_id("thermo")

    assert pr_review_identity() == "<!-- pr-agent:review:full:thermo -->"
    assert pr_review_identity(incremental=True) == "<!-- pr-agent:review:incremental:thermo -->"
    assert legacy_pr_review_header() is None
    assert get_pr_review_comment_identifiers(full=True, incremental=True) == (
        "<!-- pr-agent:review:full:thermo -->",
        "<!-- pr-agent:review:incremental:thermo -->",
    )


@pytest.mark.parametrize("value", ["Thermo", "ui review", "-ui", "a" * 41, "ui_review", 42])
def test_invalid_reviewer_id_stops_the_run(reviewer_id, value):
    reviewer_id(value)

    with pytest.raises(ValueError):
        pr_review_identity()


def test_reviewer_marker_has_both_stored_forms(reviewer_id):
    reviewer_id("ui")
    html = pr_review_identity()
    reference = "[pr-agent:review:full:ui]: https://github.com/The-PR-Agent/pr-agent"

    assert hidden_marker_forms(html) == (html, reference)
    assert render_hidden_marker(html, BitbucketProvider.__new__(BitbucketProvider)) == reference
    assert render_hidden_marker(reference) == html


@pytest.mark.parametrize("own", ["", "thermo"])
def test_review_of_another_reviewer_is_another_identity(reviewer_id, own):
    reviewer_id("ui")
    ui_body = f"## PR Reviewer Guide 🔍\n\n{pr_review_identity()}\n\nbody"
    reviewer_id(own)

    assert comment_carries_other_identity(ui_body, pr_review_identity())


@pytest.mark.parametrize("target", ["ui", "thermo", ""])
def test_each_reviewer_updates_only_its_own_comment(reviewer_id, target):
    provider = BitbucketProvider.__new__(BitbucketProvider)
    comments = {}
    for name in ("", "thermo", "ui"):
        reviewer_id(name)
        comments[name] = _review_comment(pr_review_identity(), provider)
    reviewer_id(target)

    result = _publish(provider, list(comments.values()))

    assert result is comments[target]
    provider.publish_comment.assert_not_called()
    assert provider.edit_comment.call_count == 1
    assert provider.edit_comment.call_args.args[0] is comments[target]
    assert render_hidden_marker(pr_review_identity(), provider) in provider.edit_comment.call_args.args[1]


def test_new_reviewer_adds_a_comment_and_leaves_the_others(reviewer_id):
    provider = BitbucketProvider.__new__(BitbucketProvider)
    comments = []
    for name in ("", "thermo"):
        reviewer_id(name)
        comments.append(_review_comment(pr_review_identity(), provider))
    reviewer_id("security")

    _publish(provider, comments)

    provider.edit_comment.assert_not_called()
    provider.publish_comment.assert_called_once()
    assert render_hidden_marker(pr_review_identity(), provider) in provider.publish_comment.call_args.args[0]


def test_shared_review_does_not_take_a_reviewer_comment_with_the_legacy_heading(reviewer_id):
    provider = BitbucketProvider.__new__(BitbucketProvider)
    reviewer_id("thermo")
    thermo = _review_comment(pr_review_identity(), provider)
    reviewer_id("")

    _publish(provider, [thermo])

    provider.edit_comment.assert_not_called()
    provider.publish_comment.assert_called_once()


def test_reviewer_id_from_the_command_line(reviewer_id):
    reviewer_id("")

    update_settings_from_args(["--pr_reviewer.reviewer_id=thermo"])

    assert pr_review_identity() == "<!-- pr-agent:review:full:thermo -->"


def test_reviewer_id_from_the_environment(monkeypatch):
    monkeypatch.setenv("PR_REVIEWER__REVIEWER_ID", "security")
    settings = Dynaconf(
        envvar_prefix=False,
        load_dotenv=False,
        settings_files=[f"{current_dir}/settings/configuration.toml"],
        **dynconf_kwargs,
    )
    monkeypatch.setattr(comment_identity, "get_settings", lambda: settings)

    assert pr_review_identity() == "<!-- pr-agent:review:full:security -->"

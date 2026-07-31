#!/usr/bin/env python3
"""Regression tests for deploy-run attribution and live-content verification.

Run: python3 -m unittest discover -s tests -v

The fixtures below are the real runs from the 2026-07-30 incident: publishing
commit b6024bd1 recorded run 30528951869, which actually belonged to commit
e3dcddbe and had finished ~6h earlier. Verification then read "success" off that
stale build while the live URL 404'd.

No network and no `gh` binary: the command runner and the sleeper are injected.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from deploy_run import (  # noqa: E402
    DeployRunNotFound,
    DeployRunTimeout,
    find_runs_for_sha,
    pick_deploy_run,
    resolve_deploy_run,
    sha_matches,
    wait_for_run_completion,
    wait_for_run_for_sha,
)
from verify_publish import (  # noqa: E402
    check_expectations,
    derive_body_feature,
    strip_frontmatter,
)

PUSHED_SHA = "b6024bd1eba58fad9bede1d70cfdef809a31a2b9"
PREV_SHA = "e3dcddbed339dea6e70d04378cb1047ddb5e0a63"

PREV_RUN = {
    "databaseId": 30528951869,
    "headSha": PREV_SHA,
    "status": "completed",
    "conclusion": "success",
    "workflowName": "Deploy to GitHub Pages",
    "createdAt": "2026-07-30T09:00:36Z",
    "url": "https://github.com/mashbean/blog-pro/actions/runs/30528951869",
    "event": "push",
}
NEW_RUN = {
    "databaseId": 30556924264,
    "headSha": PUSHED_SHA,
    "status": "queued",
    "conclusion": None,
    "workflowName": "Deploy to GitHub Pages",
    "createdAt": "2026-07-30T15:29:27Z",
    "url": "https://github.com/mashbean/blog-pro/actions/runs/30556924264",
    "event": "push",
}
NEW_RUN_DONE = dict(NEW_RUN, status="completed", conclusion="success")
PR_CHECK_RUN = {
    "databaseId": 30556924999,
    "headSha": PUSHED_SHA,
    "status": "completed",
    "conclusion": "success",
    "workflowName": "PR Build Check",
    "createdAt": "2026-07-30T15:29:30Z",
    "url": "https://github.com/mashbean/blog-pro/actions/runs/30556924999",
    "event": "pull_request",
}


class FakeGh:
    """Stands in for the `gh` CLI; serves scripted responses per subcommand."""

    def __init__(self, list_responses=None, view_responses=None):
        self.list_responses = list(list_responses or [])
        self.view_responses = list(view_responses or [])
        self.calls = []

    def __call__(self, cmd, cwd):
        self.calls.append(cmd)
        queue = self.view_responses if "view" in cmd else self.list_responses
        if not queue:
            raise AssertionError(f"unexpected extra gh call: {cmd}")
        # Last entry repeats, so tests only script the transitions they care about.
        payload = queue.pop(0) if len(queue) > 1 else queue[0]
        return json.dumps(payload)


class RecordingSleeper:
    def __init__(self):
        self.slept = []

    def __call__(self, seconds):
        self.slept.append(seconds)


class TestShaMatching(unittest.TestCase):
    def test_full_sha_matches_itself(self):
        self.assertTrue(sha_matches(PUSHED_SHA, PUSHED_SHA))

    def test_abbreviation_matches_full(self):
        self.assertTrue(sha_matches("b6024bd1", PUSHED_SHA))
        self.assertTrue(sha_matches(PUSHED_SHA, "b6024bd1"))

    def test_different_commits_do_not_match(self):
        self.assertFalse(sha_matches(PUSHED_SHA, PREV_SHA))

    def test_empty_or_too_short_never_matches(self):
        # Guards against a truncated value silently matching everything.
        self.assertFalse(sha_matches("", PUSHED_SHA))
        self.assertFalse(sha_matches("b6024", PUSHED_SHA))


class TestFindRunsForSha(unittest.TestCase):
    def test_ignores_newer_run_belonging_to_another_commit(self):
        """The 2026-07-30 bug: newest run != this commit's run."""
        gh = FakeGh(list_responses=[[PREV_RUN]])
        self.assertEqual(find_runs_for_sha(PUSHED_SHA, Path("."), runner=gh), [])

    def test_selects_the_run_matching_the_commit(self):
        gh = FakeGh(list_responses=[[NEW_RUN, PREV_RUN]])
        runs = find_runs_for_sha(PUSHED_SHA, Path("."), runner=gh)
        self.assertEqual([r["databaseId"] for r in runs], [30556924264])

    def test_workflow_filter_excludes_other_workflows(self):
        gh = FakeGh(list_responses=[[PR_CHECK_RUN, NEW_RUN, PREV_RUN]])
        runs = find_runs_for_sha(
            PUSHED_SHA, Path("."), workflow="Deploy to GitHub Pages", runner=gh
        )
        self.assertEqual([r["databaseId"] for r in runs], [30556924264])

    def test_empty_sha_is_rejected(self):
        with self.assertRaises(ValueError):
            find_runs_for_sha("", Path("."), runner=FakeGh(list_responses=[[]]))


class TestPickDeployRun(unittest.TestCase):
    def test_single_candidate_is_used(self):
        self.assertEqual(pick_deploy_run([NEW_RUN])["databaseId"], 30556924264)

    def test_prefers_deploy_workflow_over_pr_check(self):
        picked = pick_deploy_run([PR_CHECK_RUN, NEW_RUN])
        self.assertEqual(picked["databaseId"], 30556924264)

    def test_explicit_workflow_name_wins(self):
        picked = pick_deploy_run([PR_CHECK_RUN, NEW_RUN], workflow="PR Build Check")
        self.assertEqual(picked["databaseId"], 30556924999)

    def test_unknown_workflow_name_raises(self):
        with self.assertRaises(DeployRunNotFound):
            pick_deploy_run([NEW_RUN], workflow="Nonexistent")


class TestWaitForRunForSha(unittest.TestCase):
    def test_polls_until_github_registers_the_run(self):
        """Registration lag is the root cause — poll, don't grab the newest."""
        gh = FakeGh(list_responses=[
            [PREV_RUN],              # t+0: new run not registered yet
            [PREV_RUN],              # t+5
            [NEW_RUN, PREV_RUN],     # t+10: it appears
        ])
        sleeper = RecordingSleeper()
        runs = wait_for_run_for_sha(
            PUSHED_SHA, Path("."), timeout=30, interval=5,
            runner=gh, sleeper=sleeper,
        )
        self.assertEqual(runs[0]["databaseId"], 30556924264)
        self.assertEqual(sleeper.slept, [5, 5])

    def test_raises_instead_of_falling_back_to_newest(self):
        """The core contract: no run for the SHA means an error, not a wrong ID."""
        gh = FakeGh(list_responses=[[PREV_RUN]])
        sleeper = RecordingSleeper()
        with self.assertRaises(DeployRunNotFound) as ctx:
            wait_for_run_for_sha(
                PUSHED_SHA, Path("."), timeout=10, interval=5,
                runner=gh, sleeper=sleeper,
            )
        self.assertIn("b6024bd1eba5", str(ctx.exception))
        self.assertNotIn("30528951869", str(ctx.exception))

    def test_returns_immediately_when_already_registered(self):
        gh = FakeGh(list_responses=[[NEW_RUN, PREV_RUN]])
        sleeper = RecordingSleeper()
        wait_for_run_for_sha(
            PUSHED_SHA, Path("."), timeout=30, interval=5, runner=gh, sleeper=sleeper
        )
        self.assertEqual(sleeper.slept, [])


class TestWaitForRunCompletion(unittest.TestCase):
    def test_waits_for_queued_run_to_finish(self):
        gh = FakeGh(view_responses=[NEW_RUN, dict(NEW_RUN, status="in_progress"), NEW_RUN_DONE])
        sleeper = RecordingSleeper()
        run = wait_for_run_completion(
            30556924264, Path("."), timeout=60, interval=15, runner=gh, sleeper=sleeper
        )
        self.assertEqual(run["conclusion"], "success")
        self.assertEqual(len(sleeper.slept), 2)

    def test_times_out_when_run_never_completes(self):
        gh = FakeGh(view_responses=[NEW_RUN])
        with self.assertRaises(DeployRunTimeout):
            wait_for_run_completion(
                30556924264, Path("."), timeout=30, interval=15,
                runner=gh, sleeper=RecordingSleeper(),
            )


class TestResolveDeployRun(unittest.TestCase):
    def test_end_to_end_picks_the_right_run_for_the_commit(self):
        gh = FakeGh(list_responses=[[PREV_RUN], [PR_CHECK_RUN, NEW_RUN, PREV_RUN]])
        resolved = resolve_deploy_run(
            PUSHED_SHA, Path("."), timeout=30, interval=5,
            runner=gh, sleeper=RecordingSleeper(),
        )
        self.assertEqual(str(resolved["run"]["databaseId"]), "30556924264")
        self.assertEqual(resolved["run"]["headSha"], PUSHED_SHA)
        self.assertEqual(len(resolved["runs"]), 2)  # deploy + PR check


ARTICLE = """---
title: "形式一直在長，天花板沒有動過：中國基層參與的三十年"
slug: "2026-07-30-china-participatory-governance-rise-fall"
---

> 這篇文章由 AI 協作完成研究與初稿，題目由我設定。

## 一、「起與落」這條曲線經不起兩邊的檢查

1999 年浙江溫嶺松門鎮辦了第一場後來被稱為「民主懇談」的活動。2005 年澤國鎮以隨機抽樣的方式排定優先順序，當年的項目總需求約 1.36 億元<sup>1</sup>。
"""


class TestBodyFeature(unittest.TestCase):
    def test_strip_frontmatter(self):
        self.assertNotIn("slug:", strip_frontmatter(ARTICLE))
        self.assertNotIn("title:", strip_frontmatter(ARTICLE))

    def test_unquoted_frontmatter_never_becomes_the_body_feature(self):
        """A description renders into <meta>, so it would pass on a bodyless page."""
        article = (
            "---\n"
            "description: 中國的參與式預算走過三十年，形式一路擴張而上限沒有移動。\n"
            "---\n\n"
            "這是真正的內文第一句，用來證明頁面確實渲染了文章本體。\n"
        )
        feature = derive_body_feature(article)
        self.assertTrue(feature.startswith("這是真正的內文第一句"))

    def test_skips_frontmatter_blockquote_and_heading(self):
        feature = derive_body_feature(ARTICLE)
        self.assertTrue(feature.startswith("1999 年浙江溫嶺松門鎮"))
        self.assertNotIn("這篇文章由 AI 協作", feature)
        self.assertNotIn("起與落", feature)

    def test_feature_excludes_markup_that_rendering_would_rewrite(self):
        feature = derive_body_feature(ARTICLE)
        self.assertNotIn("<sup>", feature)
        for char in '<>&"*_[]()#':
            self.assertNotIn(char, feature)

    def test_does_not_split_inside_a_decimal_number(self):
        feature = derive_body_feature("約 1.36 億元的資金總量在當年度完成分配作業。")
        self.assertIn("1.36", feature)

    def test_returns_empty_when_no_clean_sentence_exists(self):
        self.assertEqual(derive_body_feature("---\na: b\n---\n\n## 標題\n\n> 引用\n"), "")


class TestCheckExpectations(unittest.TestCase):
    def test_all_present(self):
        body = "<h1>形式一直在長</h1><p>1999 年浙江溫嶺松門鎮辦了第一場活動。</p>"
        checks = check_expectations(body, [
            {"label": "title", "text": "形式一直在長"},
            {"label": "body", "text": "1999 年浙江溫嶺松門鎮辦了第一場活動。"},
        ])
        self.assertTrue(all(c["matched"] for c in checks))

    def test_title_present_but_body_missing_fails(self):
        """A route that renders the title but not the article must not pass."""
        checks = check_expectations("<title>形式一直在長</title><p>404</p>", [
            {"label": "title", "text": "形式一直在長"},
            {"label": "body", "text": "1999 年浙江溫嶺松門鎮辦了第一場活動。"},
        ])
        self.assertEqual([c["matched"] for c in checks], [True, False])

    def test_html_escaped_text_still_matches(self):
        checks = check_expectations("<p>A &amp; B</p>", [{"label": "t", "text": "A & B"}])
        self.assertTrue(checks[0]["matched"])

    def test_empty_expectation_never_matches(self):
        checks = check_expectations("anything", [{"label": "t", "text": ""}])
        self.assertFalse(checks[0]["matched"])


if __name__ == "__main__":
    unittest.main()

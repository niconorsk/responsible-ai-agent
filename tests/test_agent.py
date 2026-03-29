import base64
import types
from unittest.mock import MagicMock

import httpx
from pydantic_ai import Agent

from src import agent
from src.agent import FileChange, GitHubClient, GitHubConfig, MergeRequestPlan


def test_agent_module_imports():
    """Test that the agent module can be imported successfully."""
    assert isinstance(agent, types.ModuleType)


def test_agent_instance_created():
    """Test that the agent instance is a properly configured Agent."""
    assert isinstance(agent.agent, Agent)


def test_key_classes_available():
    """Test that key classes are available and are actual classes."""
    assert issubclass(agent.GitHubClient, object)
    assert issubclass(agent.GitHubConfig, object)
    assert issubclass(agent.Issue, object)
    assert issubclass(agent.MergeRequestPlan, object)
    assert issubclass(agent.MergeResult, object)


def _make_client() -> GitHubClient:
    cfg = GitHubConfig(owner="owner", repo="repo", token="token")
    return GitHubClient(cfg)


def _make_plan(*changes: FileChange) -> MergeRequestPlan:
    return MergeRequestPlan(
        issue_number=1,
        branch_name="test-branch",
        title="Test PR",
        body="Test body",
        changes=list(changes),
    )


def test_commit_changes_creates_new_file():
    """When the file does not exist (404), the PUT is called without a SHA."""
    client = _make_client()
    change = FileChange(path="new_file.py", content="print('hello')", message="add file")
    plan = _make_plan(change)

    get_resp = MagicMock()
    get_resp.status_code = 404

    put_resp = MagicMock()
    put_resp.raise_for_status = MagicMock()

    client._client.get = MagicMock(return_value=get_resp)
    client._client.put = MagicMock(return_value=put_resp)

    client.commit_changes_to_branch(plan)

    expected_content = base64.b64encode(b"print('hello')").decode()
    client._client.put.assert_called_once_with(
        "https://api.github.com/repos/owner/repo/contents/new_file.py",
        json={
            "message": "add file",
            "content": expected_content,
            "branch": "test-branch",
        },
    )
    put_resp.raise_for_status.assert_called_once()


def test_commit_changes_updates_existing_file():
    """When the file exists (200), the PUT is called with the current SHA."""
    client = _make_client()
    change = FileChange(path="existing.py", content="x = 1", message="update file")
    plan = _make_plan(change)

    get_resp = MagicMock()
    get_resp.status_code = 200
    get_resp.json = MagicMock(return_value={"sha": "abc123"})

    put_resp = MagicMock()
    put_resp.raise_for_status = MagicMock()

    client._client.get = MagicMock(return_value=get_resp)
    client._client.put = MagicMock(return_value=put_resp)

    client.commit_changes_to_branch(plan)

    expected_content = base64.b64encode(b"x = 1").decode()
    client._client.put.assert_called_once_with(
        "https://api.github.com/repos/owner/repo/contents/existing.py",
        json={
            "message": "update file",
            "content": expected_content,
            "branch": "test-branch",
            "sha": "abc123",
        },
    )
    put_resp.raise_for_status.assert_called_once()


def test_commit_changes_handles_multiple_files():
    """All file changes in the plan are committed."""
    client = _make_client()
    changes = [
        FileChange(path="a.py", content="a", message="add a"),
        FileChange(path="b.py", content="b", message="add b"),
    ]
    plan = _make_plan(*changes)

    get_resp = MagicMock()
    get_resp.status_code = 404

    put_resp = MagicMock()
    put_resp.raise_for_status = MagicMock()

    client._client.get = MagicMock(return_value=get_resp)
    client._client.put = MagicMock(return_value=put_resp)

    client.commit_changes_to_branch(plan)

    assert client._client.get.call_count == 2
    assert client._client.put.call_count == 2


def test_commit_changes_raises_on_put_failure():
    """An HTTP error from the PUT request is propagated to the caller."""
    client = _make_client()
    change = FileChange(path="bad.py", content="x", message="fail")
    plan = _make_plan(change)

    get_resp = MagicMock()
    get_resp.status_code = 404

    put_resp = MagicMock()
    put_resp.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError(
        "422 error",
        request=MagicMock(),
        response=MagicMock(),
    ))

    client._client.get = MagicMock(return_value=get_resp)
    client._client.put = MagicMock(return_value=put_resp)

    try:
        client.commit_changes_to_branch(plan)
        assert False, "Expected HTTPStatusError"
    except httpx.HTTPStatusError:
        pass


def test_commit_changes_raises_on_get_failure():
    """An unexpected HTTP error from the GET request is propagated to the caller."""
    client = _make_client()
    change = FileChange(path="forbidden.py", content="x", message="fail")
    plan = _make_plan(change)

    get_resp = MagicMock()
    get_resp.status_code = 403
    get_resp.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError(
        "403 error",
        request=MagicMock(),
        response=MagicMock(),
    ))

    client._client.get = MagicMock(return_value=get_resp)
    client._client.put = MagicMock()

    try:
        client.commit_changes_to_branch(plan)
        assert False, "Expected HTTPStatusError"
    except httpx.HTTPStatusError:
        pass

    client._client.put.assert_not_called()

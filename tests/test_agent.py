import types
from unittest.mock import MagicMock, patch

import pytest
from pydantic_ai import Agent

from src import agent
from src.agent import GitHubClient, GitHubConfig


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


@pytest.fixture()
def github_client():
    cfg = GitHubConfig(owner="test-owner", repo="test-repo", token="test-token")
    client = GitHubClient(cfg)
    yield client
    client.close()


def test_create_branch_from_default_makes_correct_api_calls(github_client):
    """Test that create_branch_from_default calls the GitHub API correctly."""
    repo_response = MagicMock()
    repo_response.json.return_value = {"default_branch": "main"}

    ref_response = MagicMock()
    ref_response.json.return_value = {"object": {"sha": "abc123"}}

    create_response = MagicMock()

    with patch.object(github_client._client, "get") as mock_get, \
         patch.object(github_client._client, "post") as mock_post:
        mock_get.side_effect = [repo_response, ref_response]
        mock_post.return_value = create_response

        github_client.create_branch_from_default("feature/new-branch")

        assert mock_get.call_count == 2
        repo_call, ref_call = mock_get.call_args_list
        assert repo_call.args[0].endswith("/repos/test-owner/test-repo")
        assert ref_call.args[0].endswith("/repos/test-owner/test-repo/git/refs/heads/main")

        mock_post.assert_called_once()
        post_call = mock_post.call_args
        assert post_call.args[0].endswith("/repos/test-owner/test-repo/git/refs")
        assert post_call.kwargs["json"] == {
            "ref": "refs/heads/feature/new-branch",
            "sha": "abc123",
        }

        create_response.raise_for_status.assert_called_once()


def test_create_branch_from_default_raises_on_ref_failure(github_client):
    """Test that create_branch_from_default propagates HTTP errors."""
    import httpx

    repo_response = MagicMock()
    repo_response.json.return_value = {"default_branch": "main"}

    error_response = httpx.Response(422, request=httpx.Request("GET", "http://example.com"))

    with patch.object(github_client._client, "get") as mock_get:
        mock_get.side_effect = [repo_response, error_response]

        with pytest.raises(httpx.HTTPStatusError):
            github_client.create_branch_from_default("feature/new-branch")

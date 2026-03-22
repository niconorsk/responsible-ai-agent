import types
import unittest.mock as mock

import httpx
from pydantic_ai import Agent

from src import agent


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
    assert issubclass(agent.NewIssue, object)
    assert issubclass(agent.MergeRequestPlan, object)
    assert issubclass(agent.MergeResult, object)


def test_create_issue_tool_registered():
    """Test that create_issue_tool is registered with the agent."""
    tool_names = list(agent.agent._function_toolset.tools.keys())
    assert "create_issue_tool" in tool_names


def test_github_client_create_issue():
    """Test that GitHubClient.create_issue posts to the GitHub API and returns an Issue."""
    cfg = agent.GitHubConfig(owner="owner", repo="repo", token="token")
    client = agent.GitHubClient(cfg)

    fake_response_data = {
        "number": 42,
        "title": "Test issue",
        "body": "Test body",
        "labels": [{"name": "bug"}],
    }
    mock_response = mock.MagicMock(spec=httpx.Response)
    mock_response.json.return_value = fake_response_data
    mock_response.raise_for_status = mock.MagicMock()

    with mock.patch.object(client._client, "post", return_value=mock_response) as mock_post:
        new_issue = agent.NewIssue(title="Test issue", body="Test body", labels=["bug"])
        result = client.create_issue(new_issue)

        mock_post.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/issues",
            json={"title": "Test issue", "body": "Test body", "labels": ["bug"]},
        )

    assert isinstance(result, agent.Issue)
    assert result.number == 42
    assert result.title == "Test issue"
    assert result.body == "Test body"
    assert result.labels == ["bug"]

    client.close()

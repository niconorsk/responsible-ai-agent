import types

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
    assert issubclass(agent.MergeRequestPlan, object)
    assert issubclass(agent.MergeResult, object)

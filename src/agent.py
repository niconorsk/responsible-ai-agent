from __future__ import annotations

import logging
import os
from typing import List

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, Tool

load_dotenv()

logger = logging.getLogger(__name__)


# ---------- Config models ----------

class GitHubConfig(BaseModel):
    owner: str
    repo: str
    token: str = Field(repr=False)


# ---------- Domain models ----------

class Issue(BaseModel):
    number: int
    title: str
    body: str | None = None
    labels: List[str] = []


class FileChange(BaseModel):
    path: str
    content: str
    message: str


class MergeRequestPlan(BaseModel):
    issue_number: int
    branch_name: str
    title: str
    body: str
    changes: List[FileChange]


class MergeResult(BaseModel):
    pull_number: int
    html_url: str
    status: str


# ---------- GitHub client (thin wrapper) ----------

class GitHubClient:
    def __init__(self, cfg: GitHubConfig):
        self.cfg = cfg
        self.base_url = "https://api.github.com"
        self._client = httpx.Client(
            headers={
                "Authorization": f"Bearer {cfg.token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=30,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def get_default_branch(self) -> str:
        url = f"{self.base_url}/repos/{self.cfg.owner}/{self.cfg.repo}"
        resp = self._client.get(url)
        resp.raise_for_status()
        return resp.json().get("default_branch", "main")

    def list_good_for_ai_issues(self) -> List[Issue]:
        url = f"{self.base_url}/repos/{self.cfg.owner}/{self.cfg.repo}/issues"
        resp = self._client.get(url, params={"state": "open", "labels": "good-for-ai"})
        resp.raise_for_status()
        issues = []
        for item in resp.json():
            labels = [l["name"] for l in item.get("labels", [])]
            issues.append(
                Issue(
                    number=item["number"],
                    title=item["title"],
                    body=item.get("body"),
                    labels=labels,
                )
            )
        return issues

    def create_branch_from_default(self, branch_name: str) -> None:
        # NOTE: this is simplified scaffolding; you'll likely want to:
        # 1. GET default branch + its latest commit SHA
        # 2. POST /git/refs to create a new branch ref
        pass

    def commit_changes_to_branch(self, plan: MergeRequestPlan) -> None:
        # NOTE: scaffolding: implement:
        # - GET file blobs / trees
        # - PUT file contents via /contents
        # or use the git data API for more control
        pass

    def open_pull_request(self, plan: MergeRequestPlan) -> MergeResult:
        url = f"{self.base_url}/repos/{self.cfg.owner}/{self.cfg.repo}/pulls"
        default_branch = self.get_default_branch()
        resp = self._client.post(
            url,
            json={
                "title": plan.title,
                "body": plan.body,
                "head": plan.branch_name,
                "base": default_branch,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return MergeResult(
            pull_number=data["number"],
            html_url=data["html_url"],
            status=data.get("state", "open"),
        )


# ---------- Tools exposed to the agent ----------

class Ctx(BaseModel):
    github: GitHubClient

    model_config = {"arbitrary_types_allowed": True}


@Tool
def list_good_for_ai_issues_tool(ctx: RunContext[Ctx]) -> List[Issue]:
    """
    List all open GitHub issues that have the 'good-for-ai' label.
    """
    return ctx.deps.github.list_good_for_ai_issues()


@Tool
def create_merge_request_tool(
    ctx: RunContext[Ctx],
    plan: MergeRequestPlan,
) -> MergeResult:
    """
    Given a merge request plan (branch + file changes + PR metadata),
    create a branch, apply changes, and open a pull request.
    """
    ctx.deps.github.create_branch_from_default(plan.branch_name)
    ctx.deps.github.commit_changes_to_branch(plan)
    return ctx.deps.github.open_pull_request(plan)


# ---------- Agent definition ----------

system_prompt = """
You are an AI code agent responsible for:

1. Scanning a GitHub repository for open issues labeled 'good-for-ai'.
2. For each suitable issue, planning a minimal, safe code change that addresses the issue.
3. Preparing a merge request (pull request) with:
   - a descriptive title
   - a clear body explaining what you changed and why
   - small, focused commits

Constraints:
- Prefer small, incremental changes over large refactors.
- If an issue is ambiguous, do NOT guess; instead, propose clarifying questions in the PR body.
- Follow existing code style and conventions inferred from the repository.
"""

agent = Agent[Ctx](
    model="gateway/openai:gpt-4.1-mini",
    system_prompt=system_prompt,
    tools=[
        list_good_for_ai_issues_tool,
        create_merge_request_tool,
    ],
)


# ---------- Orchestration / entrypoints ----------

def build_context_from_env() -> Ctx:
    cfg = GitHubConfig(
        owner=os.environ["GITHUB_OWNER"],
        repo=os.environ["GITHUB_REPO"],
        token=os.environ["GITHUB_TOKEN"],
    )
    return Ctx(github=GitHubClient(cfg))


def run_single_cycle() -> None:
    """
    One 'tick' of the agent:
    - ask it to find good-for-ai issues
    - decide which to work on
    - generate a merge request plan
    - open the PR via tools
    """
    ctx = build_context_from_env()

    # High-level instruction to the agent; it will call tools as needed.
    user_prompt = """
Scan the repository for open 'good-for-ai' issues.
Pick one that is small and well-scoped.
Then:
- design a MergeRequestPlan
- call create_merge_request_tool with that plan
Return a short summary of what you did and the PR URL.
"""

    result = agent.run_sync(user_prompt, deps=ctx)
    logger.info("Agent result: %s", result.data)
    logger.info("Agent summary: %s", result.output_text)


if __name__ == "__main__":
    run_single_cycle()

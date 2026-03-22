import os

from dotenv import load_dotenv

load_dotenv()


def main():
    github_token = os.environ.get("GITHUB_TOKEN")
    github_repo = os.environ.get("GITHUB_REPO")
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    if not github_token:
        raise EnvironmentError("GITHUB_TOKEN environment variable is not set.")
    if not github_repo:
        raise EnvironmentError("GITHUB_REPO environment variable is not set.")
    if not openai_api_key:
        raise EnvironmentError("OPENAI_API_KEY environment variable is not set.")

    print(f"Starting responsible-ai-agent for repository: {github_repo}")


if __name__ == "__main__":
    main()

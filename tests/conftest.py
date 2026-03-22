import os

# Provide a dummy API key so the pydantic_ai Agent can be instantiated at
# import time without a real OpenAI credential. Tests that exercise the agent
# at runtime will need a real key; these import-level tests do not.
os.environ.setdefault("OPENAI_API_KEY", "test-key")

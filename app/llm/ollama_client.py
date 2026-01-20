"""Utilities for interacting with Ollama."""
from openai import AsyncOpenAI, OpenAI
from typing import Any
from openai_client import OpenAIClient
from ..config.settings import settings


class OllamaClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        *,
        default_model: str = "gpt-4o",
        **client_kwargs: Any,
    ) -> None:

        self.default_model = default_model
        self.client = OpenAI(api_key=api_key, base_url=base_url)


    def execute_system__prompt(self, prompt) -> str:
        msg = {
            "role": "system",
            "content": f"{prompt}"
        }

    def execute_user_prompt(self, prompt) -> str:
        msg = {
            "role": "user",
            "content": f"{prompt}"
        }

        response = self.client.chat.completions.create(
            model="qwen/qwen3-14b",
            messages=[msg],
            temperature=0.0
        )
        print(response)

        return response.choices[0].message.content



def local_client() -> OpenAIClient:
    return OpenAIClient(
        api_key="not-needed",            # Local servers usually ignore this
        base_url="http://localhost:11434/v1"  # Change port to match your server
    )

def local_client_lmstudio() -> OpenAIClient:
    return OpenAIClient(
        api_key="not-needed",            # Local servers usually ignore this
        base_url="http://localhost:1234/v1"  # Change port to match your server
    )


def async_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.key)


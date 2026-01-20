"""Utilities for interacting with the OpenAI API."""
import re, time
from openai import AsyncOpenAI, OpenAI, ChatCompletion
from typing import Any
from app.llm.response import Response
from app.config.settings import settings


class OpenAIClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        *,
        model: str = "gpt-4o",
        **client_kwargs: Any,
    ) -> None:

        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)


    def execute_prompt(self, system_prompt: str, user_prompt: str) -> Response:
        start_time = time.time()

        response: ChatCompletion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )
        end_time = time.time()

        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        total_tokens = response.usage.total_tokens
        duration = int(end_time - start_time)
        # Calculate tokens per second
        tokens_per_sec = response.usage.completion_tokens / (end_time - start_time)

        result: Response = Response(response.choices[0].message.content, "", prompt_tokens, completion_tokens, total_tokens, duration, tokens_per_sec)

        print("-" * 60)
        # Token counts (available in response)
        print(f"Prompt tokens: {result.prompt_tokens}")
        print(f"Completion tokens: {result.completion_tokens}")
        print(f"Total tokens: {result.total_tokens}")
        # Response time
        print(f"Response time: {result.duration:.2f}s")
        print(f"Speed: {result.tokens_per_sec:.2f} tokens/sec")
        print("-" * 60)

        print(result.message)
        return response


def local_client() -> OpenAIClient:
    return OpenAIClient(
        api_key="not-needed",
        base_url="http://localhost:11434/v1",
        model="qwen3-7b"
    )

def local_client_lmstudio() -> OpenAIClient:
    return OpenAIClient(
        api_key="not-needed",
        base_url="http://localhost:1234/v1",
        model="openai/gpt-oss-20b"
    )

def async_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.key)


def _strip_think_tags(text: str) -> str:
    if not text:
        return text
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

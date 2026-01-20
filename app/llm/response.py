
from dataclasses import dataclass

@dataclass
class Response:
    message: str
    # Meta data
    think: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    duration: int
    tokens_per_sec: float

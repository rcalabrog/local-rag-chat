from abc import ABC, abstractmethod
from collections.abc import Iterator


class LLMProvider(ABC):
    @abstractmethod
    def generate_stream(self, prompt: str) -> Iterator[str]:
        raise NotImplementedError

    def generate(self, prompt: str) -> str:
        return "".join(self.generate_stream(prompt)).strip()

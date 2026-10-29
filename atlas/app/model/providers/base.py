import abc
from typing import Dict, List, Optional, AsyncGenerator


class AIProvider(abc.ABC):
    @abc.abstractmethod
    async def generate(self, prompt: str, system_prompt: str = "",
                       temperature: float = 0.7) -> str:
        pass

    @abc.abstractmethod
    async def generate_with_tools(self, prompt: str, tools: List[Dict],
                                   system_prompt: str = "",
                                   temperature: float = 0.3) -> Dict:
        pass

    @abc.abstractmethod
    async def health_check(self) -> bool:
        pass

    @abc.abstractmethod
    async def get_model_info(self) -> Dict:
        pass

    @abc.abstractmethod
    async def stream_generate(self, prompt: str,
                               system_prompt: str = "") -> AsyncGenerator[str, None]:
        pass

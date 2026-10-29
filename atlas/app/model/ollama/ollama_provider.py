import json
import logging
import asyncio
from typing import Dict, List, Optional, AsyncGenerator

import aiohttp

from atlas.app.model.providers.base import AIProvider

logger = logging.getLogger("atlas.model.ollama")


class OllamaProvider(AIProvider):
    def __init__(self, host="http://localhost:11434", model="qwen2.5:7b",
                 timeout=120, max_retries=3):
        self._host = host.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries
        self._session = None
        self._connected = False
        self._request_count = 0
        self._error_count = 0
        self._total_latency_ms = 0

    async def _get_session(self):
        try:
            curr_loop = asyncio.get_running_loop()
        except RuntimeError:
            curr_loop = None

        session_loop = getattr(self._session, "_loop", None)
        if (
            self._session is None
            or self._session.closed
            or (session_loop is not None and session_loop != curr_loop)
            or (session_loop is not None and session_loop.is_closed())
        ):
            if self._session and not self._session.closed:
                try:
                    await self._session.close()
                except Exception:
                    pass
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            )
        return self._session

    async def generate(self, prompt, system_prompt="", temperature=0.7):
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system_prompt:
            payload["system"] = system_prompt

        response = await self._request("POST", "/api/generate", payload)
        return response.get("response", "")

    async def generate_with_tools(self, prompt, tools, system_prompt="", temperature=0.3):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "tools": tools,
            "options": {"temperature": temperature},
        }

        response = await self._request("POST", "/api/chat", payload)

        result = {
            "content": "",
            "tool_calls": [],
        }

        message = response.get("message", {})
        result["content"] = message.get("content", "")

        if "tool_calls" in message:
            for tc in message["tool_calls"]:
                result["tool_calls"].append({
                    "name": tc.get("function", {}).get("name", ""),
                    "arguments": tc.get("function", {}).get("arguments", {}),
                })

        return result

    async def stream_generate(self, prompt, system_prompt=""):
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt

        session = await self._get_session()
        try:
            async with session.post(
                f"{self._host}/api/generate",
                json=payload
            ) as resp:
                async for line in resp.content:
                    if line:
                        try:
                            data = json.loads(line)
                            token = data.get("response", "")
                            if token:
                                yield token
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"[Error: {e}]"

    async def health_check(self):
        try:
            session = await self._get_session()
            async with session.get(f"{self._host}/api/tags") as resp:
                self._connected = resp.status == 200
                return self._connected
        except Exception:
            self._connected = False
            return False

    async def get_model_info(self):
        try:
            session = await self._get_session()
            async with session.get(f"{self._host}/api/tags") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = data.get("models", [])
                    for m in models:
                        if m.get("name", "").startswith(self._model.split(":")[0]):
                            return {
                                "name": m.get("name", ""),
                                "size": m.get("size", 0),
                                "modified": m.get("modified_at", ""),
                                "available": True,
                            }
                    return {"name": self._model, "available": False, "models": [m.get("name") for m in models]}
        except Exception as e:
            return {"name": self._model, "available": False, "error": str(e)}

    async def ensure_model(self):
        info = await self.get_model_info()
        if info.get("available"):
            logger.info(f"Model {self._model} is available")
            return True

        logger.info(f"Pulling model {self._model}...")
        try:
            session = await self._get_session()
            payload = {"name": self._model, "stream": False}
            async with session.post(
                f"{self._host}/api/pull",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=3600)
            ) as resp:
                if resp.status == 200:
                    logger.info(f"Model {self._model} pulled successfully")
                    return True
                else:
                    logger.error(f"Failed to pull model: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"Failed to pull model: {e}")
            return False

    async def _request(self, method, path, payload=None):
        session = await self._get_session()
        last_error = None

        for attempt in range(self._max_retries):
            try:
                import time
                start = time.perf_counter()

                if method == "POST":
                    async with session.post(f"{self._host}{path}", json=payload) as resp:
                        elapsed = (time.perf_counter() - start) * 1000
                        self._request_count += 1
                        self._total_latency_ms += elapsed

                        if resp.status == 200:
                            return await resp.json()
                        else:
                            text = await resp.text()
                            raise Exception(f"Ollama returned {resp.status}: {text[:200]}")
                else:
                    async with session.get(f"{self._host}{path}") as resp:
                        if resp.status == 200:
                            return await resp.json()
                        raise Exception(f"Ollama returned {resp.status}")

            except asyncio.TimeoutError:
                last_error = "Request timed out"
                self._error_count += 1
                logger.warning(f"Ollama timeout (attempt {attempt + 1})")
            except aiohttp.ClientError as e:
                last_error = str(e)
                self._error_count += 1
                logger.warning(f"Ollama connection error (attempt {attempt + 1}): {e}")
            except Exception as e:
                last_error = str(e)
                self._error_count += 1
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
                else:
                    raise

            if attempt < self._max_retries - 1:
                await asyncio.sleep(0.5 * (attempt + 1))

        raise Exception(f"Ollama request failed after {self._max_retries} retries: {last_error}")

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    @property
    def connected(self):
        return self._connected

    @property
    def model_name(self):
        return self._model

    def get_stats(self):
        avg = self._total_latency_ms / self._request_count if self._request_count else 0
        return {
            "host": self._host,
            "model": self._model,
            "connected": self._connected,
            "requests": self._request_count,
            "errors": self._error_count,
            "avg_latency_ms": round(avg, 1),
        }

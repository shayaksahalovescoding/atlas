import json
import logging
from typing import Dict, List, Callable, Optional
from datetime import datetime

logger = logging.getLogger("atlas.agent.tools")


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Dict] = {}
        self._handlers: Dict[str, Callable] = {}

    def register(self, name: str, description: str, parameters: Dict,
                 handler: Callable, requires_confirmation: bool = False):
        self._tools[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            }
        }
        self._handlers[name] = handler
        self._tools[name]["requires_confirmation"] = requires_confirmation

    def get_tool_schemas(self) -> List[Dict]:
        return [
            {"type": t["type"], "function": t["function"]}
            for t in self._tools.values()
        ]

    def execute(self, tool_name: str, arguments: Dict) -> Dict:
        handler = self._handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            result = handler(**arguments)
            return {"result": result}
        except Exception as e:
            logger.error(f"Tool execution error ({tool_name}): {e}", exc_info=True)
            return {"error": str(e)}

    def requires_confirmation(self, tool_name: str) -> bool:
        tool = self._tools.get(tool_name, {})
        return tool.get("requires_confirmation", False)

    def get_tool_names(self) -> List[str]:
        return list(self._tools.keys())

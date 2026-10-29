import logging
from typing import Dict, Set

logger = logging.getLogger("atlas.security.permissions")


class PermissionManager:
    def __init__(self):
        self._excluded_apps: Set[str] = set()
        self._excluded_paths: Set[str] = set()
        self._allowed_destructive_tools = set()
        self._require_confirmation_tools = {
            "terminate_process", "restart_service", "disable_service",
            "delete_file", "modify_configuration", "clear_cache",
        }

    def add_excluded_app(self, app_name: str):
        self._excluded_apps.add(app_name.lower())

    def remove_excluded_app(self, app_name: str):
        self._excluded_apps.discard(app_name.lower())

    def is_app_excluded(self, app_name: str) -> bool:
        return app_name.lower() in self._excluded_apps

    def add_excluded_path(self, path: str):
        self._excluded_paths.add(path.lower().replace("\\", "/"))

    def is_path_excluded(self, path: str) -> bool:
        path_normalized = path.lower().replace("\\", "/")
        return any(path_normalized.startswith(ep) for ep in self._excluded_paths)

    def requires_confirmation(self, tool_name: str) -> bool:
        return tool_name in self._require_confirmation_tools

    def check_tool_permission(self, tool_name: str, arguments: Dict) -> Dict:
        if tool_name in self._require_confirmation_tools:
            return {
                "allowed": False,
                "requires_confirmation": True,
                "message": f"Action '{tool_name}' requires user confirmation",
            }
        return {"allowed": True, "requires_confirmation": False}

    def get_excluded_apps(self):
        return list(self._excluded_apps)

    def get_excluded_paths(self):
        return list(self._excluded_paths)

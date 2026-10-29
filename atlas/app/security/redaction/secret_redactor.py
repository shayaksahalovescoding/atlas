import re
from typing import List


SECRET_PATTERNS = [
    re.compile(r'(?i)(password|passwd|pwd)\s*[=:]\s*\S+'),
    re.compile(r'(?i)(api[_-]?key|apikey)\s*[=:]\s*\S+'),
    re.compile(r'(?i)(secret|token|auth)\s*[=:]\s*\S+'),
    re.compile(r'(?i)(access[_-]?key|secret[_-]?key)\s*[=:]\s*\S+'),
    re.compile(r'(?i)(connection[_-]?string)\s*[=:]\s*\S+'),
    re.compile(r'(?i)(bearer\s+)\S+'),
    re.compile(r'(?i)(aws_access_key_id|aws_secret_access_key)\s*[=:]\s*\S+'),
    re.compile(r'[A-Za-z0-9+/]{40,}={0,2}'),
    re.compile(r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'),
    re.compile(r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----'),
    re.compile(r'(?i)sk-[a-zA-Z0-9]{20,}'),
    re.compile(r'(?i)ghp_[a-zA-Z0-9]{36}'),
    re.compile(r'(?i)gho_[a-zA-Z0-9]{36}'),
]

SENSITIVE_ENV_VARS = {
    "password", "passwd", "pwd", "secret", "token", "api_key",
    "apikey", "auth", "credential", "private_key", "access_key",
    "connection_string", "database_url", "redis_url",
}

REDACTED = "[REDACTED]"


def redact_command_line(cmd: str) -> str:
    if not cmd:
        return cmd
    result = cmd
    for pattern in SECRET_PATTERNS[:6]:
        result = pattern.sub(lambda m: m.group(0).split("=")[0] + "=" + REDACTED if "=" in m.group(0)
                             else m.group(0).split(":")[0] + ":" + REDACTED if ":" in m.group(0)
                             else REDACTED, result)
    return result


def redact_environment(env: dict) -> dict:
    if not env:
        return {}
    result = {}
    for key, value in env.items():
        key_lower = key.lower()
        is_sensitive = any(s in key_lower for s in SENSITIVE_ENV_VARS)
        result[key] = REDACTED if is_sensitive else value
    return result


def redact_string(text: str) -> str:
    if not text:
        return text
    result = text
    for pattern in SECRET_PATTERNS:
        result = pattern.sub(REDACTED, result)
    return result


def is_sensitive_path(path: str) -> bool:
    sensitive_parts = [
        ".ssh", ".gnupg", ".aws", "credentials", "vault",
        "keystore", ".env", "secrets",
    ]
    path_lower = path.lower().replace("\\", "/")
    return any(part in path_lower for part in sensitive_parts)

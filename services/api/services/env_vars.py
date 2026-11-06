import json
import re

from auth.security import decrypt_secret, encrypt_secret
from models.project import Project
from services.errors import DeploymentError

ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
MAX_ENV_VARS = 50
MAX_ENV_VALUE_CHARS = 4096


def validate_env_var(name: str, value: str) -> str | None:
    """Why this variable can't be saved; None if it's fine."""
    if not ENV_NAME.fullmatch(name):
        return f"Invalid variable name: {name[:50]}"
    if len(value) > MAX_ENV_VALUE_CHARS:
        return f"The value of {name} is too long."
    return None


def read_env_vars(project: Project) -> dict[str, str]:
    """The project's decrypted variables."""
    if not project.env_vars:
        return {}

    decrypted = decrypt_secret(project.env_vars)
    if decrypted is None:
        # The encryption key changed, so the stored values can't be read.
        raise DeploymentError("Environment variables could not be read. Set them again.")
    return json.loads(decrypted)


def save_env_vars(project: Project, env_vars: dict[str, str]) -> None:
    project.env_vars = encrypt_secret(json.dumps(env_vars)) if env_vars else None

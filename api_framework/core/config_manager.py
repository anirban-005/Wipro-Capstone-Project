"""Environment-aware configuration access."""
from __future__ import annotations

import configparser
import os
from pathlib import Path
from threading import Lock


class ConfigManager:
    """Thread-safe singleton that exposes the selected API environment."""

    _instance: "ConfigManager | None" = None
    _lock = Lock()

    def __new__(cls, environment: str | None = None) -> "ConfigManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._load(environment)
            elif environment and environment != cls._instance.environment:
                cls._instance._load(environment)
        return cls._instance

    def _load(self, environment: str | None) -> None:
        selected = environment or os.getenv("API_ENV", "staging")
        config_path = Path(__file__).resolve().parents[1] / "config" / "config.ini"
        parser = configparser.ConfigParser()
        loaded = parser.read(config_path)
        if not loaded:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        if selected not in parser:
            available = ", ".join(parser.sections())
            raise ValueError(f"Unknown environment '{selected}'. Available: {available}")
        self.environment = selected
        self.base_url = parser[selected]["base_url"].rstrip("/")
        self.token = os.getenv("GOREST_TOKEN", "")

    @classmethod
    def reset(cls) -> None:
        """Clear cached state; useful for isolated test runs."""
        with cls._lock:
            cls._instance = None

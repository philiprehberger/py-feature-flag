"""Simple feature flags with percentage rollout and user targeting."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from pathlib import Path
from threading import Lock
from typing import Any

__all__ = ["FlagStore", "flags"]


class FlagStore:
    """Thread-safe feature flag store with rollout and user targeting."""

    def __init__(self) -> None:
        self._flags: dict[str, Any] = {}
        self._overrides: dict[str, bool] = {}
        self._lock = Lock()
        self._callbacks: list[Callable[[str, Any, Any], None]] = []

    def on_change(self, callback: Callable[[str, Any, Any], None]) -> None:
        """Register a callback fired as ``callback(flag_name, old_value, new_value)``
        whenever a flag is loaded, set, or overridden.

        Args:
            callback: A callable receiving (flag_name, old_value, new_value).
        """
        with self._lock:
            self._callbacks.append(callback)

    def _fire_callbacks(self, name: str, old: Any, new: Any) -> None:
        """Notify all registered callbacks of a flag change."""
        for cb in self._callbacks:
            cb(name, old, new)

    def load(self, config: dict[str, Any] | str | None = None) -> None:
        """Load flags from a dict, a JSON file path, or environment variables.

        Args:
            config: A dict of flag definitions, a path to a JSON file,
                    or None to read from env vars prefixed with ``FF_``.
        """
        if config is None:
            new_flags = self._load_from_env()
        elif isinstance(config, str):
            path = Path(config)
            with path.open("r", encoding="utf-8") as fh:
                new_flags = json.load(fh)
        elif isinstance(config, dict):
            new_flags = dict(config)
        else:
            raise TypeError(
                f"config must be dict, str, or None, got {type(config).__name__}"
            )

        with self._lock:
            old_flags = self._flags
            self._flags = new_flags

        # Fire callbacks for changed/new/removed flags
        all_keys = set(old_flags) | set(new_flags)
        for key in all_keys:
            old_val = old_flags.get(key)
            new_val = new_flags.get(key)
            if old_val != new_val:
                self._fire_callbacks(key, old_val, new_val)

    def is_enabled(self, name: str, **context: Any) -> bool:
        """Check whether a flag is enabled.

        Supports plain booleans and rich configs::

            {"enabled": bool}
            {"enabled": bool, "rollout": int}        # percentage 0-100
            {"enabled": bool, "users": ["uid", ...]}  # allowlist

        For ``rollout``, the caller must pass ``user_id`` in *context*.
        For ``users``, the caller must pass ``user_id`` in *context*.
        """
        with self._lock:
            if name in self._overrides:
                return self._overrides[name]

            value = self._flags.get(name)

        if value is None:
            return False

        if isinstance(value, bool):
            return value

        if isinstance(value, dict):
            if not value.get("enabled", False):
                return False

            user_id: str | None = context.get("user_id")

            # User allowlist check
            users: list[str] | None = value.get("users")
            if users is not None:
                if user_id is not None and user_id in users:
                    return True
                if users and user_id not in (users or []):
                    return False

            # Percentage rollout check
            rollout: int | None = value.get("rollout")
            if rollout is not None:
                if user_id is None:
                    return False
                hash_val = int(
                    hashlib.md5(user_id.encode("utf-8")).hexdigest(), 16  # noqa: S324
                )
                return (hash_val % 100) < rollout

            return True

        return False

    def all(self) -> dict[str, Any]:
        """Return a copy of all loaded flags."""
        with self._lock:
            return dict(self._flags)

    def override(self, name: str, value: bool) -> None:
        """Set a runtime override for a flag."""
        with self._lock:
            old = self._overrides.get(name)
            self._overrides[name] = value
        if old != value:
            self._fire_callbacks(name, old, value)

    def reset(self) -> None:
        """Clear all runtime overrides."""
        with self._lock:
            self._overrides.clear()

    def group(self, prefix: str) -> dict[str, Any]:
        """Return resolved values for all flags whose name starts with *prefix*.

        Args:
            prefix: The prefix to filter flag names by.

        Returns:
            Dict mapping flag names to their resolved values.
        """
        with self._lock:
            matching_flags = {
                k: v for k, v in self._flags.items() if k.startswith(prefix)
            }
            overrides = dict(self._overrides)

        result: dict[str, Any] = {}
        for name, value in matching_flags.items():
            if name in overrides:
                result[name] = overrides[name]
            else:
                result[name] = value
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_from_env() -> dict[str, bool]:
        """Read ``FF_*`` environment variables as boolean flags."""
        result: dict[str, bool] = {}
        for key, value in os.environ.items():
            if key.startswith("FF_"):
                flag_name = key[3:].lower()
                result[flag_name] = value.lower() in ("1", "true", "yes", "on")
        return result


flags = FlagStore()

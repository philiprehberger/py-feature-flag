"""Simple feature flags with percentage rollout and user targeting."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from datetime import datetime, timezone
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
        self._segments: dict[str, dict[str, Any]] = {}
        self._dependencies: dict[str, list[str]] = {}
        self._schedules: dict[str, dict[str, datetime]] = {}
        self._metrics: dict[str, dict[str, int]] = {}

    # ------------------------------------------------------------------
    # Change listeners
    # ------------------------------------------------------------------

    def on_change(self, callback: Callable[[str, Any, Any], None]) -> None:
        """Register a callback fired as ``callback(flag_name, old_value, new_value)``
        whenever a flag is loaded, set, or overridden.

        Args:
            callback: A callable receiving (flag_name, old_value, new_value).
        """
        with self._lock:
            self._callbacks.append(callback)

    def remove_listener(self, callback: Callable[[str, Any, Any], None]) -> None:
        """Remove a previously registered change callback.

        Args:
            callback: The callback to remove.
        """
        with self._lock:
            self._callbacks = [cb for cb in self._callbacks if cb is not callback]

    def _fire_callbacks(self, name: str, old: Any, new: Any) -> None:
        """Notify all registered callbacks of a flag change."""
        for cb in self._callbacks:
            cb(name, old, new)

    # ------------------------------------------------------------------
    # Core flag operations
    # ------------------------------------------------------------------

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
            {"enabled": bool, "segments": ["seg"]}     # segment targeting

        For ``rollout``, the caller must pass ``user_id`` in *context*.
        For ``users``, the caller must pass ``user_id`` in *context*.
        For ``segments``, the caller must pass matching attributes in *context*.

        Respects flag dependencies, scheduled activation, and overrides.

        Each call increments per-flag usage counters tracked under
        ``export_metrics()`` (``enabled_count``, ``disabled_count``,
        ``total_evaluations``).
        """
        result = self._evaluate(name, **context)
        with self._lock:
            entry = self._metrics.get(name)
            if entry is None:
                entry = {
                    "enabled_count": 0,
                    "disabled_count": 0,
                    "total_evaluations": 0,
                }
                self._metrics[name] = entry
            entry["total_evaluations"] += 1
            if result:
                entry["enabled_count"] += 1
            else:
                entry["disabled_count"] += 1
        return result

    def _evaluate(self, name: str, **context: Any) -> bool:
        """Compute whether a flag is enabled without touching usage metrics."""
        with self._lock:
            if name in self._overrides:
                return self._overrides[name]

            value = self._flags.get(name)

        # Check schedule constraints
        schedule = self._get_schedule(name)
        if schedule is not None:
            now = context.get("now")
            if not isinstance(now, datetime):
                now = datetime.now(timezone.utc)
            activate_at = schedule.get("activate_at")
            deactivate_at = schedule.get("deactivate_at")
            if activate_at is not None and now < activate_at:
                return False
            if deactivate_at is not None and now >= deactivate_at:
                return False

        # Check flag dependencies
        deps = self._get_dependencies(name)
        if deps:
            for dep in deps:
                if not self._evaluate(dep, **context):
                    return False

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

            # Segment targeting check
            segments: list[str] | None = value.get("segments")
            if segments is not None:
                if self._matches_any_segment(segments, context):
                    return True
                if segments:
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
        """Clear all runtime overrides.

        Usage metrics are tracked independently of overrides and flag
        definitions. Calling :meth:`reset` does not clear them; use
        :meth:`reset_metrics` to zero counters.
        """
        with self._lock:
            self._overrides.clear()

    def export_metrics(self) -> dict[str, dict[str, int]]:
        """Return a snapshot of per-flag usage counters.

        Each :meth:`is_enabled` call increments counters for the flag::

            {
                "<flag_name>": {
                    "enabled_count": int,
                    "disabled_count": int,
                    "total_evaluations": int,
                },
                ...
            }

        Returns:
            A deep-copied dict that is safe to read or mutate without
            affecting the live counters.
        """
        with self._lock:
            return {k: dict(v) for k, v in self._metrics.items()}

    def reset_metrics(self) -> None:
        """Zero all usage counters without touching flag definitions.

        Flag definitions, overrides, segments, dependencies, and schedules
        are left intact — only the metrics tracked by :meth:`export_metrics`
        are cleared.
        """
        with self._lock:
            self._metrics.clear()

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
    # User segment targeting
    # ------------------------------------------------------------------

    def define_segment(
        self, name: str, attributes: dict[str, Any]
    ) -> None:
        """Define a user segment with required attribute values.

        A segment matches a user context when every attribute in the segment
        definition matches the corresponding value in the context.

        Args:
            name: Segment identifier (e.g. ``"beta_testers"``).
            attributes: Dict of attribute key-value pairs that must match.
        """
        with self._lock:
            self._segments[name] = dict(attributes)

    def remove_segment(self, name: str) -> None:
        """Remove a previously defined segment.

        Args:
            name: Segment identifier to remove.
        """
        with self._lock:
            self._segments.pop(name, None)

    def _matches_any_segment(
        self, segment_names: list[str], context: dict[str, Any]
    ) -> bool:
        """Return True if the context matches any of the named segments."""
        with self._lock:
            segments = {
                k: v for k, v in self._segments.items() if k in segment_names
            }
        for attrs in segments.values():
            if all(context.get(k) == v for k, v in attrs.items()):
                return True
        return False

    # ------------------------------------------------------------------
    # Flag dependencies
    # ------------------------------------------------------------------

    def add_dependency(self, flag: str, depends_on: str) -> None:
        """Declare that *flag* requires *depends_on* to be enabled.

        When checking ``is_enabled(flag)``, all dependencies must also
        be enabled or the flag returns ``False``.

        Args:
            flag: The flag that has the dependency.
            depends_on: The flag that must be enabled first.
        """
        with self._lock:
            self._dependencies.setdefault(flag, [])
            if depends_on not in self._dependencies[flag]:
                self._dependencies[flag].append(depends_on)

    def remove_dependency(self, flag: str, depends_on: str) -> None:
        """Remove a dependency from a flag.

        Args:
            flag: The flag to update.
            depends_on: The dependency to remove.
        """
        with self._lock:
            deps = self._dependencies.get(flag, [])
            if depends_on in deps:
                deps.remove(depends_on)
                if not deps:
                    del self._dependencies[flag]

    def _get_dependencies(self, flag: str) -> list[str]:
        """Return the list of dependencies for a flag."""
        with self._lock:
            return list(self._dependencies.get(flag, []))

    # ------------------------------------------------------------------
    # Scheduled activation
    # ------------------------------------------------------------------

    def schedule(
        self,
        name: str,
        *,
        activate_at: datetime | None = None,
        deactivate_at: datetime | None = None,
    ) -> None:
        """Schedule a flag to activate and/or deactivate at specific times.

        Scheduled times are compared against UTC. Pass a ``now`` keyword
        to ``is_enabled()`` to override the current time (useful for testing).

        Args:
            name: The flag name.
            activate_at: Enable the flag starting at this datetime.
            deactivate_at: Disable the flag starting at this datetime.
        """
        entry: dict[str, datetime] = {}
        if activate_at is not None:
            entry["activate_at"] = activate_at
        if deactivate_at is not None:
            entry["deactivate_at"] = deactivate_at
        with self._lock:
            self._schedules[name] = entry

    def remove_schedule(self, name: str) -> None:
        """Remove the schedule for a flag.

        Args:
            name: The flag name whose schedule should be removed.
        """
        with self._lock:
            self._schedules.pop(name, None)

    def _get_schedule(self, name: str) -> dict[str, datetime] | None:
        """Return the schedule for a flag, or None if not scheduled."""
        with self._lock:
            sched = self._schedules.get(name)
            return dict(sched) if sched else None

    # ------------------------------------------------------------------
    # Snapshot and restore (testing helpers)
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """Capture the full state of the store for later restoration.

        Returns a dict containing flags, overrides, segments, dependencies,
        schedules, and callbacks. Useful for test setup/teardown.

        Returns:
            A serialisable snapshot dict.
        """
        with self._lock:
            return {
                "flags": dict(self._flags),
                "overrides": dict(self._overrides),
                "segments": {k: dict(v) for k, v in self._segments.items()},
                "dependencies": {k: list(v) for k, v in self._dependencies.items()},
                "schedules": {k: dict(v) for k, v in self._schedules.items()},
                "callbacks": list(self._callbacks),
            }

    def restore(self, snap: dict[str, Any]) -> None:
        """Restore the store to a previously captured snapshot.

        Args:
            snap: A snapshot dict produced by :meth:`snapshot`.
        """
        with self._lock:
            self._flags = dict(snap.get("flags", {}))
            self._overrides = dict(snap.get("overrides", {}))
            self._segments = {
                k: dict(v) for k, v in snap.get("segments", {}).items()
            }
            self._dependencies = {
                k: list(v) for k, v in snap.get("dependencies", {}).items()
            }
            self._schedules = {
                k: dict(v) for k, v in snap.get("schedules", {}).items()
            }
            self._callbacks = list(snap.get("callbacks", []))

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

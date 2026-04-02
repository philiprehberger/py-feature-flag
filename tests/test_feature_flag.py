"""Tests for philiprehberger_feature_flag."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from philiprehberger_feature_flag import FlagStore


# ------------------------------------------------------------------
# Existing functionality
# ------------------------------------------------------------------


def test_simple_bool_flag() -> None:
    store = FlagStore()
    store.load({"dark_mode": True})
    assert store.is_enabled("dark_mode") is True


def test_disabled_flag() -> None:
    store = FlagStore()
    store.load({"beta": False})
    assert store.is_enabled("beta") is False


def test_unknown_flag_returns_false() -> None:
    store = FlagStore()
    store.load({})
    assert store.is_enabled("nonexistent") is False


def test_rollout_percentage() -> None:
    store = FlagStore()
    store.load({"experiment": {"enabled": True, "rollout": 50}})

    # Deterministic: same user_id always gets same result
    result1 = store.is_enabled("experiment", user_id="user-42")
    result2 = store.is_enabled("experiment", user_id="user-42")
    assert result1 == result2

    # With enough users, some should be in and some out
    results = {
        store.is_enabled("experiment", user_id=f"user-{i}") for i in range(200)
    }
    assert True in results
    assert False in results


def test_user_targeting() -> None:
    store = FlagStore()
    store.load({
        "vip_feature": {
            "enabled": True,
            "users": ["alice", "bob"],
        }
    })
    assert store.is_enabled("vip_feature", user_id="alice") is True
    assert store.is_enabled("vip_feature", user_id="bob") is True
    assert store.is_enabled("vip_feature", user_id="charlie") is False


def test_override() -> None:
    store = FlagStore()
    store.load({"feature": False})
    assert store.is_enabled("feature") is False

    store.override("feature", True)
    assert store.is_enabled("feature") is True

    store.reset()
    assert store.is_enabled("feature") is False


def test_load_from_dict() -> None:
    store = FlagStore()
    config = {"a": True, "b": False, "c": {"enabled": True}}
    store.load(config)
    assert store.all() == config


def test_rollout_zero_excludes_all() -> None:
    store = FlagStore()
    store.load({"feat": {"enabled": True, "rollout": 0}})
    results = [store.is_enabled("feat", user_id=f"u{i}") for i in range(100)]
    assert all(r is False for r in results)


def test_rollout_hundred_includes_all() -> None:
    store = FlagStore()
    store.load({"feat": {"enabled": True, "rollout": 100}})
    results = [store.is_enabled("feat", user_id=f"u{i}") for i in range(100)]
    assert all(r is True for r in results)


def test_disabled_dict_flag() -> None:
    store = FlagStore()
    store.load({"feat": {"enabled": False, "rollout": 100}})
    assert store.is_enabled("feat", user_id="anyone") is False


def test_on_change_callback() -> None:
    store = FlagStore()
    changes: list[tuple[str, object, object]] = []
    store.on_change(lambda name, old, new: changes.append((name, old, new)))
    store.load({"x": True})
    assert ("x", None, True) in changes


def test_group() -> None:
    store = FlagStore()
    store.load({"ui_dark": True, "ui_sidebar": False, "api_limit": 100})
    ui = store.group("ui_")
    assert ui == {"ui_dark": True, "ui_sidebar": False}
    assert "api_limit" not in ui


# ------------------------------------------------------------------
# User segment targeting
# ------------------------------------------------------------------


def test_segment_targeting_match() -> None:
    store = FlagStore()
    store.define_segment("beta_testers", {"plan": "beta", "region": "us"})
    store.load({"new_ui": {"enabled": True, "segments": ["beta_testers"]}})

    assert store.is_enabled("new_ui", plan="beta", region="us") is True


def test_segment_targeting_no_match() -> None:
    store = FlagStore()
    store.define_segment("beta_testers", {"plan": "beta", "region": "us"})
    store.load({"new_ui": {"enabled": True, "segments": ["beta_testers"]}})

    assert store.is_enabled("new_ui", plan="free", region="us") is False


def test_segment_targeting_multiple_segments() -> None:
    store = FlagStore()
    store.define_segment("admins", {"role": "admin"})
    store.define_segment("eu_users", {"region": "eu"})
    store.load({"dashboard": {"enabled": True, "segments": ["admins", "eu_users"]}})

    assert store.is_enabled("dashboard", role="admin") is True
    assert store.is_enabled("dashboard", region="eu") is True
    assert store.is_enabled("dashboard", role="viewer", region="us") is False


def test_segment_undefined_segment_no_match() -> None:
    store = FlagStore()
    store.load({"feat": {"enabled": True, "segments": ["nonexistent"]}})
    assert store.is_enabled("feat", role="admin") is False


def test_remove_segment() -> None:
    store = FlagStore()
    store.define_segment("vip", {"tier": "gold"})
    store.load({"feat": {"enabled": True, "segments": ["vip"]}})
    assert store.is_enabled("feat", tier="gold") is True

    store.remove_segment("vip")
    assert store.is_enabled("feat", tier="gold") is False


# ------------------------------------------------------------------
# Flag dependencies
# ------------------------------------------------------------------


def test_dependency_satisfied() -> None:
    store = FlagStore()
    store.load({"base": True, "advanced": True})
    store.add_dependency("advanced", "base")

    assert store.is_enabled("advanced") is True


def test_dependency_not_satisfied() -> None:
    store = FlagStore()
    store.load({"base": False, "advanced": True})
    store.add_dependency("advanced", "base")

    assert store.is_enabled("advanced") is False


def test_dependency_chain() -> None:
    store = FlagStore()
    store.load({"a": True, "b": True, "c": True})
    store.add_dependency("c", "b")
    store.add_dependency("b", "a")

    assert store.is_enabled("c") is True

    store.load({"a": False, "b": True, "c": True})
    assert store.is_enabled("c") is False


def test_dependency_multiple() -> None:
    store = FlagStore()
    store.load({"auth": True, "billing": True, "premium": True})
    store.add_dependency("premium", "auth")
    store.add_dependency("premium", "billing")

    assert store.is_enabled("premium") is True

    store.load({"auth": True, "billing": False, "premium": True})
    assert store.is_enabled("premium") is False


def test_remove_dependency() -> None:
    store = FlagStore()
    store.load({"base": False, "feat": True})
    store.add_dependency("feat", "base")
    assert store.is_enabled("feat") is False

    store.remove_dependency("feat", "base")
    assert store.is_enabled("feat") is True


# ------------------------------------------------------------------
# Scheduled activation
# ------------------------------------------------------------------


def test_schedule_activate_at_before() -> None:
    store = FlagStore()
    store.load({"launch": True})
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    store.schedule("launch", activate_at=future)

    assert store.is_enabled("launch") is False


def test_schedule_activate_at_after() -> None:
    store = FlagStore()
    store.load({"launch": True})
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    store.schedule("launch", activate_at=past)

    assert store.is_enabled("launch") is True


def test_schedule_deactivate_at_before() -> None:
    store = FlagStore()
    store.load({"promo": True})
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    store.schedule("promo", deactivate_at=future)

    assert store.is_enabled("promo") is True


def test_schedule_deactivate_at_after() -> None:
    store = FlagStore()
    store.load({"promo": True})
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    store.schedule("promo", deactivate_at=past)

    assert store.is_enabled("promo") is False


def test_schedule_window_active() -> None:
    store = FlagStore()
    store.load({"event": True})
    now = datetime.now(timezone.utc)
    store.schedule(
        "event",
        activate_at=now - timedelta(hours=1),
        deactivate_at=now + timedelta(hours=1),
    )

    assert store.is_enabled("event") is True


def test_schedule_window_expired() -> None:
    store = FlagStore()
    store.load({"event": True})
    now = datetime.now(timezone.utc)
    store.schedule(
        "event",
        activate_at=now - timedelta(hours=2),
        deactivate_at=now - timedelta(hours=1),
    )

    assert store.is_enabled("event") is False


def test_schedule_with_now_context() -> None:
    store = FlagStore()
    store.load({"feat": True})
    target = datetime(2026, 6, 1, tzinfo=timezone.utc)
    store.schedule("feat", activate_at=target)

    before = datetime(2026, 5, 31, tzinfo=timezone.utc)
    after = datetime(2026, 6, 2, tzinfo=timezone.utc)

    assert store.is_enabled("feat", now=before) is False
    assert store.is_enabled("feat", now=after) is True


def test_remove_schedule() -> None:
    store = FlagStore()
    store.load({"feat": True})
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    store.schedule("feat", activate_at=future)
    assert store.is_enabled("feat") is False

    store.remove_schedule("feat")
    assert store.is_enabled("feat") is True


# ------------------------------------------------------------------
# Flag change listeners
# ------------------------------------------------------------------


def test_remove_listener() -> None:
    store = FlagStore()
    changes: list[tuple[str, object, object]] = []

    def listener(name: str, old: object, new: object) -> None:
        changes.append((name, old, new))

    store.on_change(listener)
    store.load({"a": True})
    assert len(changes) == 1

    store.remove_listener(listener)
    store.load({"b": True})
    # Listener was removed, so "b" change should not be recorded
    assert len(changes) == 1


def test_multiple_listeners() -> None:
    store = FlagStore()
    log1: list[str] = []
    log2: list[str] = []

    store.on_change(lambda n, o, v: log1.append(n))
    store.on_change(lambda n, o, v: log2.append(n))
    store.load({"x": True})

    assert "x" in log1
    assert "x" in log2


def test_override_fires_callback() -> None:
    store = FlagStore()
    changes: list[tuple[str, object, object]] = []
    store.on_change(lambda n, o, v: changes.append((n, o, v)))
    store.override("feat", True)
    assert ("feat", None, True) in changes


# ------------------------------------------------------------------
# Snapshot and restore
# ------------------------------------------------------------------


def test_snapshot_and_restore_flags() -> None:
    store = FlagStore()
    store.load({"a": True, "b": False})
    snap = store.snapshot()

    store.load({"c": True})
    assert store.all() == {"c": True}

    store.restore(snap)
    assert store.all() == {"a": True, "b": False}


def test_snapshot_and_restore_overrides() -> None:
    store = FlagStore()
    store.load({"feat": False})
    store.override("feat", True)
    snap = store.snapshot()

    store.reset()
    assert store.is_enabled("feat") is False

    store.restore(snap)
    assert store.is_enabled("feat") is True


def test_snapshot_and_restore_segments() -> None:
    store = FlagStore()
    store.define_segment("vip", {"tier": "gold"})
    store.load({"feat": {"enabled": True, "segments": ["vip"]}})
    snap = store.snapshot()

    store.remove_segment("vip")
    assert store.is_enabled("feat", tier="gold") is False

    store.restore(snap)
    assert store.is_enabled("feat", tier="gold") is True


def test_snapshot_and_restore_dependencies() -> None:
    store = FlagStore()
    store.load({"base": False, "child": True})
    store.add_dependency("child", "base")
    snap = store.snapshot()

    store.remove_dependency("child", "base")
    assert store.is_enabled("child") is True

    store.restore(snap)
    assert store.is_enabled("child") is False


def test_snapshot_and_restore_schedules() -> None:
    store = FlagStore()
    store.load({"feat": True})
    future = datetime(2099, 1, 1, tzinfo=timezone.utc)
    store.schedule("feat", activate_at=future)
    snap = store.snapshot()

    store.remove_schedule("feat")
    assert store.is_enabled("feat") is True

    store.restore(snap)
    assert store.is_enabled("feat") is False


def test_snapshot_and_restore_callbacks() -> None:
    store = FlagStore()
    log: list[str] = []
    store.on_change(lambda n, o, v: log.append(n))
    snap = store.snapshot()

    store.remove_listener(snap["callbacks"][0])
    store.load({"x": True})
    assert "x" not in log

    store.restore(snap)
    store.load({"y": True})
    assert "y" in log


def test_snapshot_is_isolated_copy() -> None:
    store = FlagStore()
    store.load({"a": True})
    snap = store.snapshot()

    # Mutating snap should not affect the store
    snap["flags"]["a"] = False
    assert store.is_enabled("a") is True

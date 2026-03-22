"""Tests for philiprehberger_feature_flag."""

from __future__ import annotations

from philiprehberger_feature_flag import FlagStore


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

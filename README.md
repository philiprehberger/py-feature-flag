# philiprehberger-feature-flag

[![Tests](https://github.com/philiprehberger/py-feature-flag/actions/workflows/publish.yml/badge.svg)](https://github.com/philiprehberger/py-feature-flag/actions/workflows/publish.yml)
[![PyPI version](https://img.shields.io/pypi/v/philiprehberger-feature-flag.svg)](https://pypi.org/project/philiprehberger-feature-flag/)
[![Last updated](https://img.shields.io/github/last-commit/philiprehberger/py-feature-flag)](https://github.com/philiprehberger/py-feature-flag/commits/main)

Simple feature flags with percentage rollout and user targeting.

## Installation

```bash
pip install philiprehberger-feature-flag
```

## Usage

```python
from philiprehberger_feature_flag import flags

flags.load({"dark_mode": True, "beta_ui": False})

if flags.is_enabled("dark_mode"):
    enable_dark_mode()
```

### Percentage rollout

```python
from philiprehberger_feature_flag import flags

flags.load({
    "new_checkout": {
        "enabled": True,
        "rollout": 25,  # 25% of users
    }
})

if flags.is_enabled("new_checkout", user_id="user-42"):
    show_new_checkout()
```

### User targeting

```python
from philiprehberger_feature_flag import flags

flags.load({
    "admin_panel": {
        "enabled": True,
        "users": ["alice", "bob"],
    }
})

if flags.is_enabled("admin_panel", user_id="alice"):
    show_admin_panel()
```

### Segment targeting

```python
from philiprehberger_feature_flag import flags

flags.define_segment("beta_testers", {"plan": "beta", "region": "us"})
flags.load({
    "new_ui": {
        "enabled": True,
        "segments": ["beta_testers"],
    }
})

if flags.is_enabled("new_ui", plan="beta", region="us"):
    show_new_ui()
```

### Flag dependencies

```python
from philiprehberger_feature_flag import flags

flags.load({"auth": True, "billing": True, "premium": True})
flags.add_dependency("premium", "auth")
flags.add_dependency("premium", "billing")

# premium is only enabled when both auth and billing are enabled
flags.is_enabled("premium")  # True
```

### Scheduled activation

```python
from datetime import datetime, timezone
from philiprehberger_feature_flag import flags

flags.load({"launch": True})
flags.schedule(
    "launch",
    activate_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    deactivate_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
)

# Flag is only enabled between July 1 and August 1
flags.is_enabled("launch")
```

### Change callbacks

```python
from philiprehberger_feature_flag import flags

def on_flag_change(name, old, new):
    print(f"Flag {name} changed from {old} to {new}")

flags.on_change(on_flag_change)
flags.load({"dark_mode": True})
# prints: Flag dark_mode changed from None to True

flags.remove_listener(on_flag_change)
```

### Snapshot and restore

```python
from philiprehberger_feature_flag import flags

flags.load({"feature_a": True, "feature_b": False})
snap = flags.snapshot()

# Modify state for testing
flags.override("feature_b", True)
assert flags.is_enabled("feature_b")

# Restore original state
flags.restore(snap)
assert not flags.is_enabled("feature_b")
```

### Load from JSON file

```python
from philiprehberger_feature_flag import flags

flags.load("flags.json")
```

### Load from environment variables

```python
from philiprehberger_feature_flag import flags

# Set FF_DARK_MODE=true, FF_BETA=0, etc.
flags.load()  # reads FF_* env vars
```

### Runtime overrides

```python
from philiprehberger_feature_flag import flags

flags.override("beta_ui", True)   # force-enable for testing
flags.reset()                     # clear all overrides
```

### Flag groups

```python
from philiprehberger_feature_flag import flags

flags.load({
    "ui_dark_mode": True,
    "ui_sidebar": False,
    "api_rate_limit": 100,
})

ui_flags = flags.group("ui_")
# {"ui_dark_mode": True, "ui_sidebar": False}
```

## API

| Function / Class | Description |
|---|---|
| `FlagStore()` | Create a new flag store |
| `store.load(config)` | Load flags from dict, JSON file path, or env vars (`None`) |
| `store.is_enabled(name, **context)` | Check if a flag is enabled |
| `store.all()` | Return all loaded flags as a dict |
| `store.override(name, value)` | Set a runtime override |
| `store.reset()` | Clear all runtime overrides |
| `store.on_change(callback)` | Register a callback fired as `callback(flag_name, old_value, new_value)` on changes |
| `store.remove_listener(callback)` | Remove a previously registered change callback |
| `store.group(prefix)` | Return dict of flags whose name starts with `prefix` with resolved values |
| `store.define_segment(name, attributes)` | Define a user segment with required attribute key-value pairs |
| `store.remove_segment(name)` | Remove a previously defined segment |
| `store.add_dependency(flag, depends_on)` | Declare that `flag` requires `depends_on` to be enabled |
| `store.remove_dependency(flag, depends_on)` | Remove a dependency from a flag |
| `store.schedule(name, activate_at, deactivate_at)` | Schedule a flag to activate/deactivate at specific datetimes |
| `store.remove_schedule(name)` | Remove the schedule for a flag |
| `store.snapshot()` | Capture full store state (flags, overrides, segments, dependencies, schedules) |
| `store.restore(snap)` | Restore the store to a previously captured snapshot |
| `flags` | Module-level `FlagStore` instance |

## Development

```bash
pip install -e .
python -m pytest tests/ -v
```

## Support

If you find this project useful:

⭐ [Star the repo](https://github.com/philiprehberger/py-feature-flag)

🐛 [Report issues](https://github.com/philiprehberger/py-feature-flag/issues?q=is%3Aissue+is%3Aopen+label%3Abug)

💡 [Suggest features](https://github.com/philiprehberger/py-feature-flag/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)

❤️ [Sponsor development](https://github.com/sponsors/philiprehberger)

🌐 [All Open Source Projects](https://philiprehberger.com/open-source-packages)

💻 [GitHub Profile](https://github.com/philiprehberger)

🔗 [LinkedIn Profile](https://www.linkedin.com/in/philiprehberger)

## License

[MIT](LICENSE)

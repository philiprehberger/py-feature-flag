# philiprehberger-feature-flag

[![Tests](https://github.com/philiprehberger/py-feature-flag/actions/workflows/publish.yml/badge.svg)](https://github.com/philiprehberger/py-feature-flag/actions/workflows/publish.yml)
[![PyPI version](https://img.shields.io/pypi/v/philiprehberger-feature-flag.svg)](https://pypi.org/project/philiprehberger-feature-flag/)
[![GitHub release](https://img.shields.io/github/v/release/philiprehberger/py-feature-flag)](https://github.com/philiprehberger/py-feature-flag/releases)
[![Last updated](https://img.shields.io/github/last-commit/philiprehberger/py-feature-flag)](https://github.com/philiprehberger/py-feature-flag/commits/main)
[![License](https://img.shields.io/github/license/philiprehberger/py-feature-flag)](LICENSE)
[![Bug Reports](https://img.shields.io/github/issues/philiprehberger/py-feature-flag/bug)](https://github.com/philiprehberger/py-feature-flag/issues?q=is%3Aissue+is%3Aopen+label%3Abug)
[![Feature Requests](https://img.shields.io/github/issues/philiprehberger/py-feature-flag/enhancement)](https://github.com/philiprehberger/py-feature-flag/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)
[![Sponsor](https://img.shields.io/badge/sponsor-GitHub%20Sponsors-ec6cb9)](https://github.com/sponsors/philiprehberger)

Simple feature flags with percentage rollout and user targeting.

## Installation

```bash
pip install philiprehberger-feature-flag
```

## Usage

### Basic flags

```python
from philiprehberger_feature_flag import flags

flags.load({"dark_mode": True, "beta_ui": False})

if flags.is_enabled("dark_mode"):
    enable_dark_mode()
```

### Percentage rollout

```python
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
flags.load({
    "admin_panel": {
        "enabled": True,
        "users": ["alice", "bob"],
    }
})

if flags.is_enabled("admin_panel", user_id="alice"):
    show_admin_panel()
```

### Load from JSON file

```python
flags.load("flags.json")
```

### Load from environment variables

```python
# Set FF_DARK_MODE=true, FF_BETA=0, etc.
flags.load()  # reads FF_* env vars
```

### Runtime overrides

```python
flags.override("beta_ui", True)   # force-enable for testing
flags.reset()                     # clear all overrides
```

### Change callbacks

```python
def on_flag_change(name, old, new):
    print(f"Flag {name} changed from {old} to {new}")

flags.on_change(on_flag_change)
flags.load({"dark_mode": True})
# prints: Flag dark_mode changed from None to True
```

### Flag groups

```python
flags.load({
    "ui_dark_mode": True,
    "ui_sidebar": False,
    "api_rate_limit": 100,
})

ui_flags = flags.group("ui_")
# {"ui_dark_mode": True, "ui_sidebar": False}
```

## API

| Function / Method | Description |
|---|---|
| `FlagStore()` | Create a new flag store |
| `store.load(config)` | Load flags from dict, JSON file path, or env vars (`None`) |
| `store.is_enabled(name, **context)` | Check if a flag is enabled |
| `store.all()` | Return all loaded flags as a dict |
| `store.override(name, value)` | Set a runtime override |
| `store.reset()` | Clear all runtime overrides |
| `store.on_change(callback)` | Register a callback fired as `callback(flag_name, old_value, new_value)` on changes |
| `store.group(prefix)` | Return dict of flags whose name starts with `prefix` with resolved values |
| `flags` | Module-level `FlagStore` instance |

## Development

```bash
pip install -e .
python -m pytest tests/ -v
```

## Support

If you find this package useful, consider starring the repository.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Philip%20Rehberger-blue?logo=linkedin)](https://www.linkedin.com/in/philiprehberger/)
[![More packages](https://img.shields.io/badge/More%20packages-philiprehberger-orange)](https://github.com/philiprehberger?tab=repositories)

## License

[MIT](LICENSE)

# philiprehberger-feature-flag

[![Tests](https://github.com/philiprehberger/py-feature-flag/actions/workflows/publish.yml/badge.svg)](https://github.com/philiprehberger/py-feature-flag/actions/workflows/publish.yml)
[![PyPI version](https://img.shields.io/pypi/v/philiprehberger-feature-flag.svg)](https://pypi.org/project/philiprehberger-feature-flag/)
[![License](https://img.shields.io/github/license/philiprehberger/py-feature-flag)](LICENSE)

Simple feature flags with percentage rollout and user targeting.

## Installation

```bash
pip install philiprehberger-feature-flag
```

## Usage

### Basic Flags

```python
from philiprehberger_feature_flag import flags

flags.load({"dark_mode": True, "beta_ui": False})

if flags.is_enabled("dark_mode"):
    enable_dark_mode()
```

### Percentage Rollout

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

### User Targeting

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

### Load from JSON File

```python
flags.load("flags.json")
```

### Load from Environment Variables

```python
# Set FF_DARK_MODE=true, FF_BETA=0, etc.
flags.load()  # reads FF_* env vars
```

### Runtime Overrides

```python
flags.override("beta_ui", True)   # force-enable for testing
flags.reset()                     # clear all overrides
```

## API

| Function / Method | Description |
| --- | --- |
| `FlagStore()` | Create a new flag store |
| `store.load(config)` | Load flags from dict, JSON file path, or env vars (`None`) |
| `store.is_enabled(name, **context)` | Check if a flag is enabled |
| `store.all()` | Return all loaded flags as a dict |
| `store.override(name, value)` | Set a runtime override |
| `store.reset()` | Clear all runtime overrides |
| `flags` | Module-level `FlagStore` instance |

## Development

```bash
pip install -e .
python -m pytest tests/ -v
```

## License

MIT

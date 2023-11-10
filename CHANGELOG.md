# Changelog

## 0.3.0 (2026-04-01)

- Add user segment targeting with `define_segment()` and `remove_segment()` for enabling flags by user group attributes
- Add flag dependencies with `add_dependency()` and `remove_dependency()` so flags can require other flags to be enabled
- Add scheduled activation with `schedule()` and `remove_schedule()` to enable/disable flags at specific datetimes
- Add `remove_listener()` to unregister change callbacks
- Add `snapshot()` and `restore()` for capturing and replaying full store state in tests

## 0.2.1 (2026-03-31)

- Standardize README to 3-badge format with emoji Support section
- Update CI checkout action to v5 for Node.js 24 compatibility

## 0.2.0 (2026-03-27)

- Add `on_change(callback)` for registering change callbacks on flag load, set, or override
- Add `group(prefix)` to retrieve all flags matching a namespace prefix with resolved values
- Callbacks fire with `(flag_name, old_value, new_value)` signature

## 0.1.0 (2026-03-21)

- Initial release
- Boolean, percentage rollout, and user targeting flags
- Load from dict, JSON file, or environment variables
- Thread-safe with runtime overrides

# Changelog

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

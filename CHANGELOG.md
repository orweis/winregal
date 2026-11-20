# Changelog

## 2.0.0 - Unreleased

### Breaking
- Dropped Python 2 and Python < 3.9; packaging moved to `pyproject.toml`.
- Enumeration/`to_dict`/iteration now raise on errors other than "no more items" (previously
  swallowed, returning partial data). `key[name]` only falls back to a sub-key when no value
  is found.
- Sub-paths are joined with explicit backslashes: leading separators no longer escape the
  parent key; `/` and `:` are ordinary characters.
- Re-entering an open `RegKey` raises `WinregalException`.
- `WinregalException` now derives from `OSError` (identical to `WindowsError` on Windows).
- `RegValue.__repr__` changed; `RegValue` compares by value (and is unhashable, so it can no
  longer be used in sets or as a dict key).
- An unknown explicit `hkey` now raises `UnknownHkeyException` (an `OSError`) instead of
  `KeyError`; `except KeyError` handlers must be updated.
- `to_dict(keep_type=True)` now returns `RegValue` objects for values in nested keys too
  (previously bare data); the shape of the result changes for nested keys.
- `repr(RegKey)` no longer has a trailing backslash for hive roots.

### Fixed
- Bare hive paths such as `RegKey("HKEY_CURRENT_USER")` no longer raise `TypeError`.
- Hive names are checked against the real HKEY_* list (see Breaking for the exception type).
- `to_dict(keep_type=True)` is applied to nested keys (see Breaking).
- `__exit__` is idempotent; no more `SyntaxWarning` for invalid escape sequences.
- Module imports on non-Windows when a `winreg` stand-in is provided (used by tests).

### Added
- `to_dict(max_depth=...)`, type hints and `py.typed`, pytest suite, GitHub Actions CI
  (Linux and Windows, Python 3.9-3.14), migration notes in the README.

## 1.0.1
- Last release before this changelog.

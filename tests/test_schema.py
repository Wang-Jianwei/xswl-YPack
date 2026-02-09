"""Tests for YAML schema validation."""

from __future__ import annotations

import pytest

from ypack.schema import CONFIG_SCHEMA, ConfigValidationError, validate_config


class TestValidateConfig:
    """Tests for :func:`validate_config`."""

    def test_minimal_valid(self):
        """Only ``app.name`` is required at the schema level."""
        validate_config({"app": {"name": "Foo"}})

    def test_missing_app(self):
        with pytest.raises(ConfigValidationError, match="app"):
            validate_config({"files": []})

    def test_missing_app_name(self):
        with pytest.raises(ConfigValidationError, match="name"):
            validate_config({"app": {"version": "1"}})

    def test_invalid_root_type(self):
        with pytest.raises(ConfigValidationError):
            validate_config("not-a-dict")

    def test_invalid_registry_hive(self):
        """Unknown registry hive should fail."""
        data = {
            "app": {"name": "T"},
            "install": {
                "registry_entries": [
                    {"hive": "INVALID", "key": "k", "name": "n", "value": "v"}
                ]
            },
        }
        try:
            import jsonschema  # noqa: F401
        except ImportError:
            pytest.skip("jsonschema not installed — deep validation skipped")
        with pytest.raises(ConfigValidationError):
            validate_config(data)

    def test_invalid_env_scope(self):
        data = {
            "app": {"name": "T"},
            "install": {
                "env_vars": [{"name": "X", "value": "Y", "scope": "global"}]
            },
        }
        try:
            import jsonschema  # noqa: F401
        except ImportError:
            pytest.skip("jsonschema not installed")
        with pytest.raises(ConfigValidationError):
            validate_config(data)

    def test_valid_full_config(self):
        data = {
            "app": {"name": "Big", "version": "2.0", "publisher": "P", "description": "D"},
            "install": {
                "install_dir": "$PROGRAMFILES64\\Big",
                "desktop_shortcut": {"target": "$INSTDIR\\Big.exe"},
                "registry_entries": [
                    {"hive": "HKLM", "key": "Software\\Big", "name": "Path", "value": "$INSTDIR"}
                ],
                "env_vars": [
                    {"name": "BIG_HOME", "value": "$INSTDIR", "scope": "system"}
                ],
                "file_associations": [
                    {"extension": ".big"}
                ],
            },
            "files": ["a.exe", {"source": "lib/*", "destination": "$INSTDIR\\lib"}],
            "languages": ["English", "SimplifiedChinese"],
            "signing": {"enabled": False},
            "update": {"enabled": False},
            "logging": {"enabled": True, "level": "DEBUG"},
        }
        validate_config(data)  # should not raise

    def test_typo_in_install_section(self):
        """Typo in field name (desktop_shortcuts → desktop_shortcut) should fail."""
        data = {
            "app": {"name": "T"},
            "install": {
                "desktop_shortcuts": {"target": "$INSTDIR\\T.exe"}  # TYPO: should be desktop_shortcut
            },
        }
        try:
            import jsonschema  # noqa: F401
        except ImportError:
            pytest.skip("jsonschema not installed")
        with pytest.raises(ConfigValidationError, match="additionalProperties|desktop_shortcuts"):
            validate_config(data)

    def test_typo_in_app_section(self):
        """Typo in app field should fail."""
        data = {
            "app": {
                "name": "T",
                "publisherr": "P",  # TYPO: should be publisher
            }
        }
        try:
            import jsonschema  # noqa: F401
        except ImportError:
            pytest.skip("jsonschema not installed")
        with pytest.raises(ConfigValidationError, match="additionalProperties|publisherr"):
            validate_config(data)

    def test_typo_in_logging_section(self):
        """Typo in logging field should fail."""
        data = {
            "app": {"name": "T"},
            "logging": {
                "enabled": True,
                "levelll": "DEBUG",  # TYPO: should be level
            }
        }
        try:
            import jsonschema  # noqa: F401
        except ImportError:
            pytest.skip("jsonschema not installed")
        with pytest.raises(ConfigValidationError, match="additionalProperties|levelll"):
            validate_config(data)


class TestConfigValidationError:
    def test_message_formatting(self):
        err = ConfigValidationError(["bad field A", "bad field B"])
        assert "bad field A" in str(err)
        assert "bad field B" in str(err)
        assert err.errors == ["bad field A", "bad field B"]

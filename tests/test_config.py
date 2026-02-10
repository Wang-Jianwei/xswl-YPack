"""Tests for ypack.config — configuration parsing."""

from __future__ import annotations

import os
import tempfile

import pytest
import yaml

from ypack.config import (
    AppInfo,
    EnvVarEntry,
    FileAssociation,
    FileEntry,
    InstallConfig,
    LoggingConfig,
    PackageConfig,
    PackageEntry,
    RegistryEntry,
    SigningConfig,
    SystemRequirements,
    UpdateConfig,
)


# -----------------------------------------------------------------------
# AppInfo
# -----------------------------------------------------------------------

class TestAppInfo:
    def test_basic(self):
        app = AppInfo.from_dict({"name": "A", "version": "1.0", "publisher": "P"})
        assert app.name == "A"
        assert app.version == "1.0"

    def test_uninstall_icon_fallback(self):
        app = AppInfo.from_dict({"name": "A", "version": "1.0", "install_icon": "x.ico"})
        assert app.uninstall_icon == "x.ico"


# -----------------------------------------------------------------------
# FileEntry
# -----------------------------------------------------------------------

class TestFileEntry:
    def test_from_string(self):
        fe = FileEntry.from_dict("test.exe")
        assert fe.source == "test.exe"
        assert fe.destination == "$INSTDIR"
        # 'recursive' field removed; recursion is determined from source pattern
        assert not hasattr(fe, 'recursive')

    def test_from_dict(self):
        # Use '**' pattern to indicate recursion (no explicit recursive key)
        fe = FileEntry.from_dict({"source": "lib/**/*", "destination": "$INSTDIR\\lib"})
        from ypack.converters.nsis_sections import _should_use_recursive
        assert _should_use_recursive(fe.source)

    def test_remote(self):
        fe = FileEntry.from_dict({"source": "https://x.com/f.bin", "checksum_type": "sha256", "checksum_value": "abc", "decompress": True})
        assert fe.is_remote
        assert fe.decompress

    def test_legacy_download_url(self):
        fe = FileEntry.from_dict({"source": "f.bin", "download_url": "https://x.com/f.bin"})
        assert fe.is_remote


# -----------------------------------------------------------------------
# InstallConfig (depends on FileAssociation, SystemRequirements)
# -----------------------------------------------------------------------

class TestInstallConfig:
    def test_registry_entries(self):
        ic = InstallConfig.from_dict({
            "registry_entries": [{"hive": "HKLM", "key": "k", "name": "n", "value": "v"}],
        })
        assert len(ic.registry_entries) == 1

    def test_env_vars(self):
        ic = InstallConfig.from_dict({
            "env_vars": [{"name": "X", "value": "Y", "scope": "user"}],
        })
        assert ic.env_vars[0].scope == "user"

    def test_file_associations(self):
        ic = InstallConfig.from_dict({
            "file_associations": [{"extension": ".foo", "prog_id": "Foo.File"}],
        })
        assert ic.file_associations[0].extension == ".foo"

    def test_system_requirements(self):
        ic = InstallConfig.from_dict({
            "system_requirements": {"min_windows_version": "10.0", "require_admin": True},
        })
        assert ic.system_requirements is not None
        assert ic.system_requirements.require_admin

    def test_silent_install(self):
        ic = InstallConfig.from_dict({"silent_install": True})
        assert ic.silent_install


# -----------------------------------------------------------------------
# PackageConfig
# -----------------------------------------------------------------------

class TestPackageConfig:
    MINIMAL = {"app": {"name": "T", "version": "1.0"}, "install": {}, "files": ["a.exe"]}

    def test_from_dict(self):
        cfg = PackageConfig.from_dict(self.MINIMAL)
        assert cfg.app.name == "T"
        assert len(cfg.files) == 1

    def test_from_yaml(self, tmp_path):
        p = tmp_path / "cfg.yaml"
        p.write_text(yaml.dump(self.MINIMAL), encoding="utf-8")
        cfg = PackageConfig.from_yaml(str(p))
        assert cfg.app.name == "T"
        assert cfg._config_dir == str(tmp_path)

    def test_signing(self):
        d = {**self.MINIMAL, "signing": {"enabled": True, "certificate": "c.pfx", "password": "p"}}
        cfg = PackageConfig.from_dict(d)
        assert cfg.signing is not None and cfg.signing.enabled

    def test_update(self):
        d = {**self.MINIMAL, "update": {"enabled": True, "update_url": "https://u", "download_url": "https://d"}}
        cfg = PackageConfig.from_dict(d)
        assert cfg.update is not None
        assert cfg.update.download_url == "https://d"
    def test_languages_default(self):
        cfg = PackageConfig.from_dict(self.MINIMAL)
        # Default: empty list means system language will be used (no MUI_LANGUAGE)
        assert cfg.languages == []

    def test_languages_custom(self):
        d = {**self.MINIMAL, "languages": ["English", "SimplifiedChinese"]}
        cfg = PackageConfig.from_dict(d)
        assert len(cfg.languages) == 2
        assert cfg.languages[0].name == "English"
        assert cfg.languages[1].name == "SimplifiedChinese"

    def test_logging(self):
        d = {**self.MINIMAL, "logging": {"enabled": True, "path": "C:\\logs", "level": "DEBUG"}}
        cfg = PackageConfig.from_dict(d)
        assert cfg.logging is not None
        assert cfg.logging.level == "DEBUG"

    def test_packages_with_children(self):
        d = {
            **self.MINIMAL,
            "packages": {
                "Drivers": {
                    "children": {
                        "PXI": {"sources": [{"source": "pxi/*", "destination": "$INSTDIR\\pxi"}], "optional": True}
                    }
                }
            },
        }
        cfg = PackageConfig.from_dict(d)
        assert len(cfg.packages) == 1
        assert len(cfg.packages[0].children) == 1
        assert cfg.packages[0].children[0].optional

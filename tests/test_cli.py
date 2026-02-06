"""Tests for the CLI interface."""

from __future__ import annotations

import os
import textwrap

import pytest

from ypack.cli import main


@pytest.fixture()
def yaml_file(tmp_path):
    """Write a minimal valid YAML and return its path."""
    p = tmp_path / "test.yaml"
    p.write_text(
        textwrap.dedent("""\
            app:
              name: CLIApp
              version: "1.0"
            install: {}
            files:
              - app.exe
        """),
        encoding="utf-8",
    )
    return str(p)


class TestConvertSubcommand:
    def test_convert_creates_nsi(self, yaml_file, tmp_path):
        out = str(tmp_path / "out.nsi")
        main(["convert", yaml_file, "-o", out])
        assert os.path.exists(out)
        content = open(out, encoding="utf-8").read()
        assert "CLIApp" in content

    def test_dry_run_no_file(self, yaml_file, tmp_path, capsys):
        out = str(tmp_path / "should_not_exist.nsi")
        main(["convert", yaml_file, "-o", out, "--dry-run"])
        assert not os.path.exists(out)
        captured = capsys.readouterr()
        assert "CLIApp" in captured.out

    def test_missing_config_exits(self, tmp_path):
        with pytest.raises(SystemExit):
            main(["convert", str(tmp_path / "no_such.yaml")])

    def test_verbose(self, yaml_file, tmp_path, capsys):
        out = str(tmp_path / "v.nsi")
        main(["convert", yaml_file, "-o", out, "-v"])
        captured = capsys.readouterr()
        assert "Loading" in captured.out or "Converting" in captured.out or "NSIS" in captured.out


class TestFormatOption:
    def test_default_format_nsis(self, yaml_file, tmp_path):
        out = str(tmp_path / "out.nsi")
        main(["convert", yaml_file, "-o", out])
        content = open(out, encoding="utf-8").read()
        assert "Unicode true" in content

    def test_explicit_nsis(self, yaml_file, tmp_path):
        out = str(tmp_path / "out.nsi")
        main(["convert", yaml_file, "-f", "nsis", "-o", out])
        assert os.path.exists(out)

    def test_unknown_format_exits(self, yaml_file):
        with pytest.raises(SystemExit):
            main(["convert", yaml_file, "-f", "unknown"])


class TestInitSubcommand:
    def test_creates_template(self, tmp_path):
        out = str(tmp_path / "new.yaml")
        main(["init", "-o", out])
        assert os.path.exists(out)
        content = open(out, encoding="utf-8").read()
        assert "MyApp" in content

    def test_refuses_overwrite(self, tmp_path):
        out = str(tmp_path / "existing.yaml")
        with open(out, "w") as f:
            f.write("existing")
        with pytest.raises(SystemExit):
            main(["init", "-o", out])


class TestValidateSubcommand:
    def test_valid_file(self, yaml_file, capsys):
        main(["validate", yaml_file])
        captured = capsys.readouterr()
        assert "valid" in captured.out.lower() or "✓" in captured.out

    def test_invalid_file(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("files: [x]\n", encoding="utf-8")
        with pytest.raises(SystemExit):
            main(["validate", str(bad)])

    def test_verbose_output(self, yaml_file, capsys):
        main(["validate", yaml_file, "-v"])
        captured = capsys.readouterr()
        assert "CLIApp" in captured.out


class TestVersionFlag:
    def test_version(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

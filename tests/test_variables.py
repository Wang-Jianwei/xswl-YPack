"""Tests for variable system and resolver."""

from __future__ import annotations

import pytest

from ypack.variables import (
    BUILTIN_VARIABLES,
    YPACK_LANGUAGES,
    LanguageDefinition,
    VariableDefinition,
    VariableRegistry,
)
from ypack.resolver import CircularReferenceError, VariableResolver, create_resolver


# -----------------------------------------------------------------------
# VariableDefinition
# -----------------------------------------------------------------------

class TestVariableDefinition:
    def test_get_nsis(self):
        vd = BUILTIN_VARIABLES["INSTDIR"]
        assert vd.get_value("nsis") == "$INSTDIR"

    def test_get_wix(self):
        vd = BUILTIN_VARIABLES["INSTDIR"]
        assert vd.get_value("wix") == "[INSTALLDIR]"

    def test_get_inno(self):
        vd = BUILTIN_VARIABLES["INSTDIR"]
        assert vd.get_value("inno") == "{app}"

    def test_unsupported_tool(self):
        vd = VariableDefinition(name="X", description="", nsis="$X")
        with pytest.raises(ValueError, match="not defined for tool 'wix'"):
            vd.get_value("wix")


# -----------------------------------------------------------------------
# LanguageDefinition
# -----------------------------------------------------------------------

class TestLanguageDefinition:
    def test_known_languages(self):
        assert "English" in YPACK_LANGUAGES
        assert "SimplifiedChinese" in YPACK_LANGUAGES
        assert "Japanese" in YPACK_LANGUAGES

    def test_nsis_mapping(self):
        assert YPACK_LANGUAGES["SimplifiedChinese"].get_value("nsis") == "SimplifiedChinese"


# -----------------------------------------------------------------------
# VariableRegistry
# -----------------------------------------------------------------------

class TestVariableRegistry:
    def test_builtin_names(self):
        reg = VariableRegistry("nsis")
        names = reg.get_builtin_variable_names()
        assert "INSTDIR" in names
        assert "PROGRAMFILES64" in names
        assert "TEMP" in names

    def test_resolve_builtin(self):
        reg = VariableRegistry("nsis")
        assert reg.resolve_builtin_var("INSTDIR") == "$INSTDIR"

    def test_unknown_builtin_returns_none(self):
        reg = VariableRegistry("nsis")
        assert reg.resolve_builtin_var("DOES_NOT_EXIST") is None

    def test_custom_variables(self):
        reg = VariableRegistry("nsis")
        reg.add_custom_variable("MY_DIR", "C:\\mydir")
        assert reg.get_custom_variable("MY_DIR") == "C:\\mydir"
        assert reg.validate_variable("MY_DIR")

    def test_validate_strict(self):
        reg = VariableRegistry("nsis")
        with pytest.raises(ValueError, match="Unknown variable"):
            reg.validate_variable("NOPE", strict=True)


# -----------------------------------------------------------------------
# VariableResolver
# -----------------------------------------------------------------------

class TestVariableResolver:
    def _make_resolver(self, config_dict=None):
        return create_resolver(config_dict or {}, "nsis")

    def test_resolve_config_ref(self):
        r = self._make_resolver({"app": {"name": "Foo"}})
        assert r.resolve("${app.name}") == "Foo"

    def test_resolve_nested(self):
        r = self._make_resolver({
            "app": {"name": "Bar"},
            "variables": {"DATA": "C:\\${app.name}\\data"},
        })
        # variables.DATA → C:\${app.name}\data → C:\Bar\data
        assert r.resolve("${variables.DATA}") == "C:\\Bar\\data"

    def test_builtin_passthrough(self):
        r = self._make_resolver({})
        # NSIS builtins stay as NSIS syntax
        assert r.resolve("$INSTDIR\\sub") == "$INSTDIR\\sub"

    def test_unknown_config_ref_kept(self):
        r = self._make_resolver({})
        assert r.resolve("${does.not.exist}") == "${does.not.exist}"

    def test_circular_reference_detection(self):
        r = self._make_resolver({
            "variables": {"A": "${variables.B}", "B": "${variables.A}"},
        })
        with pytest.raises(CircularReferenceError):
            r.resolve("${variables.A}")

    def test_max_depth(self):
        # Build a chain that exceeds MAX_DEPTH
        depth = VariableResolver.MAX_DEPTH + 2
        cfg: dict = {"variables": {}}
        for i in range(depth):
            cfg["variables"][f"v{i}"] = f"${{variables.v{i + 1}}}"
        cfg["variables"][f"v{depth}"] = "end"
        r = self._make_resolver(cfg)
        with pytest.raises(RecursionError):
            r.resolve("${variables.v0}")

    def test_escaped_dollar(self):
        r = self._make_resolver({})
        assert r.resolve("$$FOO") == "$FOO"

    def test_empty_input(self):
        r = self._make_resolver({})
        assert r.resolve("") == ""
        assert r.resolve(None) is None  # type: ignore[arg-type]

    def test_validate_references(self):
        r = self._make_resolver({"app": {"name": "X"}})
        unknown = r.validate_references("${app.name} $INSTDIR $BOGUS_VAR")
        assert "$BOGUS_VAR" in unknown

    def test_validate_strict(self):
        r = self._make_resolver({})
        with pytest.raises(ValueError, match="Unknown variable"):
            r.validate_references("$UNKNOWN_VAR", strict=True)


# -----------------------------------------------------------------------
# create_resolver factory
# -----------------------------------------------------------------------

class TestCreateResolver:
    def test_custom_vars_loaded(self):
        r = create_resolver({"variables": {"MY": "hello"}}, "nsis")
        assert r.resolve("${variables.MY}") == "hello"

    def test_target_tool_wix(self):
        r = create_resolver({"variables": {}}, "wix")
        assert r.registry.target_tool == "wix"

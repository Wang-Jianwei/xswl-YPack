"""
Unit tests for variable system
"""

import pytest
from ypack.variables import VariableRegistry, VariableDefinition, BUILTIN_VARIABLES
from ypack.resolver import VariableResolver, CircularReferenceError, create_resolver


class TestVariableDefinition:
    """Test VariableDefinition class"""
    
    def test_get_value_nsis(self):
        var_def = VariableDefinition(
            name="TEST",
            description="Test variable",
            nsis="$TEST",
            wix="[TEST]",
            inno="{test}"
        )
        assert var_def.get_value("nsis") == "$TEST"
        assert var_def.get_value("NSIS") == "$TEST"  # Case insensitive
    
    def test_get_value_wix(self):
        var_def = BUILTIN_VARIABLES["INSTDIR"]
        assert var_def.get_value("wix") == "[INSTALLDIR]"
    
    def test_get_value_unsupported_tool(self):
        var_def = VariableDefinition(
            name="TEST",
            description="Test",
            nsis="$TEST"
        )
        with pytest.raises(ValueError, match="not defined for tool"):
            var_def.get_value("wix")


class TestVariableRegistry:
    """Test VariableRegistry class"""
    
    def test_builtin_variables_loaded(self):
        registry = VariableRegistry("nsis")
        assert "INSTDIR" in registry.get_builtin_variable_names()
        assert "PROGRAMFILES64" in registry.get_builtin_variable_names()
    
    def test_resolve_builtin_var_nsis(self):
        registry = VariableRegistry("nsis")
        assert registry.resolve_builtin_var("INSTDIR") == "$INSTDIR"
        assert registry.resolve_builtin_var("PROGRAMFILES64") == "$PROGRAMFILES64"
        assert registry.resolve_builtin_var("APPDATA") == "$APPDATA"
    
    def test_resolve_builtin_var_wix(self):
        registry = VariableRegistry("wix")
        assert registry.resolve_builtin_var("INSTDIR") == "[INSTALLDIR]"
        assert registry.resolve_builtin_var("PROGRAMFILES64") == "[ProgramFiles64Folder]"
    
    def test_resolve_builtin_var_unknown(self):
        registry = VariableRegistry("nsis")
        assert registry.resolve_builtin_var("UNKNOWN_VAR") is None
    
    def test_custom_variables(self):
        registry = VariableRegistry("nsis")
        registry.add_custom_variable("MY_PATH", "$APPDATA\\MyApp")
        assert registry.get_custom_variable("MY_PATH") == "$APPDATA\\MyApp"
        assert registry.get_custom_variable("UNKNOWN") is None
    
    def test_validate_variable(self):
        registry = VariableRegistry("nsis")
        registry.add_custom_variable("CUSTOM", "value")
        
        assert registry.validate_variable("INSTDIR") is True
        assert registry.validate_variable("CUSTOM") is True
        assert registry.validate_variable("UNKNOWN") is False
    
    def test_validate_variable_strict(self):
        registry = VariableRegistry("nsis")
        with pytest.raises(ValueError, match="Unknown variable"):
            registry.validate_variable("UNKNOWN_VAR", strict=True)


class TestVariableResolver:
    """Test VariableResolver class"""
    
    def test_resolve_config_reference(self):
        config = {
            "app": {"name": "TestApp", "version": "1.0"},
            "install": {"dir": "C:\\Program Files"}
        }
        resolver = create_resolver(config, "nsis")
        
        assert resolver.resolve("${app.name}") == "TestApp"
        assert resolver.resolve("${app.version}") == "1.0"
        assert resolver.resolve("${install.dir}") == "C:\\Program Files"
    
    def test_resolve_builtin_variable_nsis(self):
        config = {}
        resolver = create_resolver(config, "nsis")
        
        assert resolver.resolve("$INSTDIR") == "$INSTDIR"
        assert resolver.resolve("$PROGRAMFILES64") == "$PROGRAMFILES64"
        assert resolver.resolve("$APPDATA\\MyApp") == "$APPDATA\\MyApp"
    
    def test_resolve_builtin_variable_wix(self):
        config = {}
        resolver = create_resolver(config, "wix")
        
        assert resolver.resolve("$INSTDIR") == "[INSTALLDIR]"
        assert resolver.resolve("$PROGRAMFILES64") == "[ProgramFiles64Folder]"
    
    def test_resolve_mixed_variables(self):
        config = {
            "app": {"name": "MyApp", "publisher": "ACME"}
        }
        resolver = create_resolver(config, "nsis")
        
        result = resolver.resolve("$PROGRAMFILES64\\${app.publisher}\\${app.name}")
        assert result == "$PROGRAMFILES64\\ACME\\MyApp"
    
    def test_resolve_custom_variables(self):
        config = {
            "app": {"name": "MyApp"},
            "variables": {
                "DATA_DIR": "$APPDATA\\${app.name}"
            }
        }
        resolver = create_resolver(config, "nsis")
        
        # Custom variable should be expanded first, then config ref, then builtin
        result = resolver.resolve("${variables.DATA_DIR}\\logs")
        assert result == "$APPDATA\\MyApp\\logs"
    
    def test_resolve_nested_references(self):
        config = {
            "app": {"name": "MyApp"},
            "paths": {
                "base": "$PROGRAMFILES64\\${app.name}",
                "config": "${paths.base}\\config"
            }
        }
        resolver = create_resolver(config, "nsis")
        
        result = resolver.resolve("${paths.config}")
        assert result == "$PROGRAMFILES64\\MyApp\\config"
    
    def test_circular_reference_detection(self):
        config = {
            "a": "${b}",
            "b": "${a}"
        }
        resolver = create_resolver(config, "nsis")
        
        with pytest.raises(CircularReferenceError, match="Circular reference"):
            resolver.resolve("${a}")
    
    def test_circular_reference_self(self):
        config = {
            "value": "${value}"
        }
        resolver = create_resolver(config, "nsis")
        
        with pytest.raises(CircularReferenceError):
            resolver.resolve("${value}")
    
    def test_circular_reference_chain(self):
        config = {
            "a": "${b}",
            "b": "${c}",
            "c": "${a}"
        }
        resolver = create_resolver(config, "nsis")
        
        # Just check that circular reference is detected (order may vary)
        with pytest.raises(CircularReferenceError, match="Circular reference"):
            resolver.resolve("${a}")
    
    def test_max_depth_exceeded(self):
        config = {
            "a": "${b}",
            "b": "${c}",
            "c": "${d}",
            "d": "${e}",
            "e": "${f}",
            "f": "${g}",
            "g": "${h}",
            "h": "${i}",
            "i": "${j}",
            "j": "${k}",
            "k": "${l}",
            "l": "value"
        }
        resolver = create_resolver(config, "nsis")
        
        with pytest.raises(RecursionError, match="max depth"):
            resolver.resolve("${a}")
    
    def test_unknown_reference_preserved(self):
        config = {"app": {"name": "MyApp"}}
        resolver = create_resolver(config, "nsis")
        
        # Unknown reference should be preserved
        result = resolver.resolve("${unknown.reference}")
        assert result == "${unknown.reference}"
    
    def test_escaped_dollar_sign(self):
        config = {}
        resolver = create_resolver(config, "nsis")
        
        # $$ should become literal $
        result = resolver.resolve("$$INSTDIR is the install directory")
        assert result == "$INSTDIR is the install directory"
    
    def test_validate_references(self):
        config = {"app": {"name": "MyApp"}}
        resolver = create_resolver(config, "nsis")
        
        unknown = resolver.validate_references("${app.name} $INSTDIR ${unknown}")
        assert "${unknown}" in unknown
        assert len(unknown) == 1
    
    def test_validate_references_strict(self):
        config = {"app": {"name": "MyApp"}}
        resolver = create_resolver(config, "nsis")
        
        with pytest.raises(ValueError, match="Unknown variable"):
            resolver.validate_references("${unknown.ref}", strict=True)


class TestIntegration:
    """Integration tests with real-world scenarios"""
    
    def test_registry_entry_resolution(self):
        config = {
            "app": {"name": "SigVNA", "publisher": "SIGLENT"},
            "install": {"install_dir": "$PROGRAMFILES64\\${app.publisher}\\${app.name}"}
        }
        resolver = create_resolver(config, "nsis")
        
        # Registry key
        key = resolver.resolve("Software\\${app.publisher}\\${app.name}")
        assert key == "Software\\SIGLENT\\SigVNA"
        
        # Registry value
        value = resolver.resolve("$INSTDIR")
        assert value == "$INSTDIR"
    
    def test_file_destination_resolution(self):
        config = {
            "app": {"name": "MyApp"},
            "variables": {"DATA_DIR": "$APPDATA\\${app.name}"}
        }
        resolver = create_resolver(config, "nsis")
        
        dest = resolver.resolve("${variables.DATA_DIR}\\config")
        assert dest == "$APPDATA\\MyApp\\config"
    
    def test_environment_variable_resolution(self):
        config = {
            "app": {"name": "MyTool"},
            "install": {"install_dir": "$PROGRAMFILES64\\${app.name}"}
        }
        resolver = create_resolver(config, "nsis")
        
        env_value = resolver.resolve("${install.install_dir}\\bin")
        assert env_value == "$PROGRAMFILES64\\MyTool\\bin"

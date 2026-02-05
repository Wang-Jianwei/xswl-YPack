"""
Variable resolver for configuration references.

Handles resolution of:
- Built-in variables: $VAR
- Config references: ${path.to.value}
- Custom variables: ${variables.NAME}
"""

import re
from typing import Any, Dict, Set, Optional


class CircularReferenceError(Exception):
    """Raised when a circular reference is detected in variable resolution."""
    pass


class VariableResolver:
    """Resolves variable references in configuration strings."""
    
    MAX_DEPTH = 10  # Maximum recursion depth to prevent infinite loops
    
    def __init__(self, config_dict: Dict[str, Any], variable_registry):
        """Initialize the resolver.
        
        Args:
            config_dict: The full configuration dictionary (parsed YAML)
            variable_registry: VariableRegistry instance for built-in variable mapping
        """
        self.config = config_dict
        self.registry = variable_registry
        self._resolving_stack: Set[str] = set()
    
    def resolve(self, text: str, depth: int = 0) -> str:
        """Resolve all variable references in text.
        
        Resolution order:
        1. ${config.path.to.value} - Configuration references
        2. $BUILTIN_VAR - Built-in runtime variables
        
        Args:
            text: Text containing variable references
            depth: Current recursion depth (for cycle detection)
            
        Returns:
            Text with all variables resolved
            
        Raises:
            RecursionError: If max depth exceeded
            CircularReferenceError: If circular reference detected
        """
        if not text or not isinstance(text, str):
            return text
        
        # Depth protection
        if depth > self.MAX_DEPTH:
            raise RecursionError(
                f"Variable resolution exceeded max depth ({self.MAX_DEPTH}). "
                "Possible circular reference or overly complex nesting."
            )
        
        # Phase 1: Resolve ${...} config references
        text = self._resolve_config_references(text, depth)
        
        # Phase 2: Resolve $VAR built-in variables
        text = self._resolve_builtin_variables(text)
        
        return text
    
    def _resolve_config_references(self, text: str, depth: int) -> str:
        """Resolve ${path.to.value} style references.
        
        Args:
            text: Text containing ${...} references
            depth: Current recursion depth
            
        Returns:
            Text with ${...} references resolved
        """
        pattern = r'\$\{([^}]+)\}'
        
        def replace_match(match):
            ref_path = match.group(1)  # e.g., "app.name" or "variables.DATA_DIR"
            
            # Circular reference detection
            if ref_path in self._resolving_stack:
                chain = ' → '.join(self._resolving_stack) + f' → {ref_path}'
                raise CircularReferenceError(
                    f"Circular reference detected: {chain}"
                )
            
            # Add to resolution stack
            self._resolving_stack.add(ref_path)
            try:
                # Get value from config
                value = self._get_value_by_path(ref_path)
                if value is None:
                    # Reference not found - keep original
                    return match.group(0)
                
                # Recursively resolve (value might contain more references)
                resolved = self.resolve(str(value), depth + 1)
                return resolved
            finally:
                # Remove from stack
                self._resolving_stack.discard(ref_path)
        
        return re.sub(pattern, replace_match, text)
    
    def _resolve_builtin_variables(self, text: str) -> str:
        """Resolve $VAR style built-in variables.
        
        Args:
            text: Text containing $VAR references
            
        Returns:
            Text with $VAR references converted to target tool format
        """
        # Match $WORD but not ${...} (already handled)
        # Also handle escaped $$ → $
        
        # First protect escaped $$
        text = text.replace('$$', '\x00ESCAPED_DOLLAR\x00')
        
        # Pattern: $VARNAME where VARNAME is uppercase letters/underscores
        pattern = r'\$([A-Z_][A-Z0-9_]*)'
        
        def replace_match(match):
            var_name = match.group(1)
            
            # Try to resolve as built-in variable
            resolved = self.registry.resolve_builtin_var(var_name)
            if resolved is not None:
                return resolved
            
            # Unknown variable - keep as-is (will be caught by validation if strict)
            return match.group(0)
        
        text = re.sub(pattern, replace_match, text)
        
        # Restore escaped dollars
        text = text.replace('\x00ESCAPED_DOLLAR\x00', '$')
        
        return text
    
    def _get_value_by_path(self, path: str) -> Optional[Any]:
        """Get a value from config dict using dot-separated path.
        
        Args:
            path: Dot-separated path like 'app.name' or 'install.install_dir'
            
        Returns:
            Value at the path, or None if not found
        """
        obj = self.config
        for key in path.split('.'):
            if isinstance(obj, dict):
                obj = obj.get(key)
            else:
                return None
            if obj is None:
                return None
        return obj
    
    def validate_references(self, text: str, strict: bool = False) -> list:
        """Validate all variable references in text.
        
        Args:
            text: Text to validate
            strict: If True, raise exception for unknown variables
            
        Returns:
            List of unknown variable names (empty if all valid)
            
        Raises:
            ValueError: If strict=True and unknown variables found
        """
        if not text or not isinstance(text, str):
            return []
        
        unknown = []
        
        # Check ${...} references
        config_refs = re.findall(r'\$\{([^}]+)\}', text)
        for ref_path in config_refs:
            value = self._get_value_by_path(ref_path)
            if value is None:
                unknown.append(f'${{{ref_path}}}')
        
        # Check $VAR references
        builtin_refs = re.findall(r'\$([A-Z_][A-Z0-9_]*)', text)
        for var_name in builtin_refs:
            if not self.registry.validate_variable(var_name, strict=False):
                unknown.append(f'${var_name}')
        
        if unknown and strict:
            raise ValueError(
                f"Unknown variable references found: {', '.join(unknown)}"
            )
        
        return unknown


def create_resolver(config_dict: Dict[str, Any], target_tool: str = "nsis"):
    """Factory function to create a VariableResolver.
    
    Args:
        config_dict: Parsed YAML configuration dictionary
        target_tool: Target installer tool ('nsis', 'wix', 'inno')
        
    Returns:
        Configured VariableResolver instance
    """
    from .variables import VariableRegistry
    
    registry = VariableRegistry(target_tool)
    
    # Add custom variables from config if present
    custom_vars = config_dict.get('variables', {})
    if isinstance(custom_vars, dict):
        for name, value in custom_vars.items():
            if isinstance(value, str):
                registry.add_custom_variable(name, value)
    
    return VariableResolver(config_dict, registry)

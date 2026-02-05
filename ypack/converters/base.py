"""
Base converter interfaces for packaging tools.
"""

from abc import ABC
from typing import Dict, Any


class BaseConverter(ABC):
    """Base class for tool-specific converters."""

    tool_name = "generic"

    def __init__(self, config, raw_config: Dict[str, Any] = None):
        """Initialize the converter.
        
        Args:
            config: PackageConfig instance
            raw_config: Raw configuration dictionary (for variable resolution)
        """
        self.config = config
        self.raw_config = raw_config or {}
        
        # Initialize variable resolver
        from ..resolver import create_resolver
        self.resolver = create_resolver(self.raw_config, self.tool_name)
    
    def resolve_variables(self, text: str) -> str:
        """Resolve all variable references in text.
        
        Handles:
        - Built-in variables: $INSTDIR, $PROGRAMFILES64, etc.
        - Config references: ${app.name}, ${install.install_dir}, etc.
        - Custom variables: ${variables.XXX}
        
        Args:
            text: Text containing variable references
            
        Returns:
            Text with all variables resolved
        """
        if not text or not isinstance(text, str):
            return text
        return self.resolver.resolve(text)

    def _warn_unsupported(self, feature: str) -> str:
        """Return a standardized comment for unsupported features."""
        return f"; [UNSUPPORTED by {self.tool_name}] {feature}"
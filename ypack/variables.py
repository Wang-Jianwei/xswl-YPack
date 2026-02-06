"""
Variable system for cross-platform installer configuration.

Defines built-in variables and their mappings across different installer tools
(NSIS, WIX, Inno Setup, etc.), as well as language identifiers.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class LanguageDefinition:
    """Definition of a ypack language identifier and its tool-specific mappings."""
    
    name: str
    description: str
    nsis: str  # NSIS MUI language identifier (usually same as ypack name)
    wix: Optional[str] = None
    inno: Optional[str] = None
    
    def get_value(self, target_tool: str) -> str:
        """Get the language identifier for a specific installer tool.
        
        Args:
            target_tool: Target installer tool ('nsis', 'wix', 'inno')
            
        Returns:
            Tool-specific language identifier
            
        Raises:
            ValueError: If target_tool is not supported
        """
        tool_map = {
            'nsis': self.nsis,
            'wix': self.wix,
            'inno': self.inno,
        }
        
        value = tool_map.get(target_tool.lower())
        if value is None:
            raise ValueError(
                f"Language '{self.name}' is not defined for tool '{target_tool}'. "
                f"Available tools: {[k for k, v in tool_map.items() if v is not None]}"
            )
        return value


# ypack language definitions (cross-platform language identifiers)
YPACK_LANGUAGES: Dict[str, LanguageDefinition] = {
    "English": LanguageDefinition(
        name="English",
        description="English (US)",
        nsis="English",
    ),
    "SimplifiedChinese": LanguageDefinition(
        name="SimplifiedChinese",
        description="Simplified Chinese (Mainland China)",
        nsis="SimplifiedChinese",
    ),
    "TraditionalChinese": LanguageDefinition(
        name="TraditionalChinese",
        description="Traditional Chinese (Taiwan / Hong Kong)",
        nsis="TraditionalChinese",
    ),
    "French": LanguageDefinition(
        name="French",
        description="French (France)",
        nsis="French",
    ),
    "German": LanguageDefinition(
        name="German",
        description="German (Germany)",
        nsis="German",
    ),
    "Spanish": LanguageDefinition(
        name="Spanish",
        description="Spanish (Spain)",
        nsis="Spanish",
    ),
    "Japanese": LanguageDefinition(
        name="Japanese",
        description="Japanese (Japan)",
        nsis="Japanese",
    ),
    "Korean": LanguageDefinition(
        name="Korean",
        description="Korean (South Korea)",
        nsis="Korean",
    ),
    "Russian": LanguageDefinition(
        name="Russian",
        description="Russian (Russia)",
        nsis="Russian",
    ),
    "Portuguese": LanguageDefinition(
        name="Portuguese",
        description="Portuguese (Portugal)",
        nsis="Portuguese",
    ),
    "BrazilianPortuguese": LanguageDefinition(
        name="BrazilianPortuguese",
        description="Portuguese (Brazil)",
        nsis="BrazilianPortuguese",
    ),
    "Polish": LanguageDefinition(
        name="Polish",
        description="Polish (Poland)",
        nsis="Polish",
    ),
    "Czech": LanguageDefinition(
        name="Czech",
        description="Czech (Czech Republic)",
        nsis="Czech",
    ),
    "Turkish": LanguageDefinition(
        name="Turkish",
        description="Turkish (Turkey)",
        nsis="Turkish",
    ),
    "Hungarian": LanguageDefinition(
        name="Hungarian",
        description="Hungarian (Hungary)",
        nsis="Hungarian",
    ),
}


@dataclass
class VariableDefinition:
    """Definition of a cross-platform variable."""
    
    name: str
    description: str
    nsis: str
    wix: Optional[str] = None
    inno: Optional[str] = None
    
    def get_value(self, target_tool: str) -> str:
        """Get the variable value for a specific installer tool.
        
        Args:
            target_tool: Target installer tool ('nsis', 'wix', 'inno')
            
        Returns:
            Tool-specific variable string
            
        Raises:
            ValueError: If target_tool is not supported
        """
        tool_map = {
            'nsis': self.nsis,
            'wix': self.wix,
            'inno': self.inno,
        }
        
        value = tool_map.get(target_tool.lower())
        if value is None:
            raise ValueError(
                f"Variable '{self.name}' is not defined for tool '{target_tool}'. "
                f"Available tools: {[k for k, v in tool_map.items() if v is not None]}"
            )
        return value


# Built-in variable definitions
BUILTIN_VARIABLES: Dict[str, VariableDefinition] = {
    "INSTDIR": VariableDefinition(
        name="INSTDIR",
        description="Installation directory chosen by user",
        nsis="$INSTDIR",
        wix="[INSTALLDIR]",
        inno="{app}",
    ),
    
    "PROGRAMFILES": VariableDefinition(
        name="PROGRAMFILES",
        description="Program Files folder (32-bit on 64-bit systems)",
        nsis="$PROGRAMFILES",
        wix="[ProgramFilesFolder]",
        inno="{pf}",
    ),
    
    "PROGRAMFILES64": VariableDefinition(
        name="PROGRAMFILES64",
        description="Program Files folder (64-bit)",
        nsis="$PROGRAMFILES64",
        wix="[ProgramFiles64Folder]",
        inno="{pf64}",
    ),
    
    "APPDATA": VariableDefinition(
        name="APPDATA",
        description="Application Data folder (roaming)",
        nsis="$APPDATA",
        wix="[AppDataFolder]",
        inno="{userappdata}",
    ),
    
    "LOCALAPPDATA": VariableDefinition(
        name="LOCALAPPDATA",
        description="Local Application Data folder (non-roaming)",
        nsis="$LOCALAPPDATA",
        wix="[LocalAppDataFolder]",
        inno="{localappdata}",
    ),
    
    "DESKTOP": VariableDefinition(
        name="DESKTOP",
        description="Desktop folder",
        nsis="$DESKTOP",
        wix="[DesktopFolder]",
        inno="{userdesktop}",
    ),
    
    "STARTMENU": VariableDefinition(
        name="STARTMENU",
        description="Start Menu folder",
        nsis="$STARTMENU",
        wix="[StartMenuFolder]",
        inno="{userstartmenu}",
    ),
    
    "SMPROGRAMS": VariableDefinition(
        name="SMPROGRAMS",
        description="Start Menu Programs folder",
        nsis="$SMPROGRAMS",
        wix="[ProgramMenuFolder]",
        inno="{userprograms}",
    ),
    
    "TEMP": VariableDefinition(
        name="TEMP",
        description="Temporary folder",
        nsis="$TEMP",
        wix="[TempFolder]",
        inno="{tmp}",
    ),
    
    "WINDIR": VariableDefinition(
        name="WINDIR",
        description="Windows directory",
        nsis="$WINDIR",
        wix="[WindowsFolder]",
        inno="{win}",
    ),
    
    "SYSDIR": VariableDefinition(
        name="SYSDIR",
        description="System32 directory",
        nsis="$SYSDIR",
        wix="[SystemFolder]",
        inno="{sys}",
    ),
    
    "COMMONFILES": VariableDefinition(
        name="COMMONFILES",
        description="Common Files folder",
        nsis="$COMMONFILES",
        wix="[CommonFilesFolder]",
        inno="{cf}",
    ),
    
    "COMMONFILES64": VariableDefinition(
        name="COMMONFILES64",
        description="Common Files folder (64-bit)",
        nsis="$COMMONFILES64",
        wix="[CommonFiles64Folder]",
        inno="{cf64}",
    ),
    
    "DOCUMENTS": VariableDefinition(
        name="DOCUMENTS",
        description="My Documents folder",
        nsis="$DOCUMENTS",
        wix="[PersonalFolder]",
        inno="{userdocs}",
    ),
}


class VariableRegistry:
    """Registry for managing built-in and custom variables."""
    
    def __init__(self, target_tool: str = "nsis"):
        """Initialize the variable registry.
        
        Args:
            target_tool: Target installer tool ('nsis', 'wix', 'inno')
        """
        self.target_tool = target_tool.lower()
        self.builtin_vars = BUILTIN_VARIABLES.copy()
        self.custom_vars: Dict[str, str] = {}
    
    def get_builtin_variable_names(self) -> set:
        """Get all built-in variable names."""
        return set(self.builtin_vars.keys())
    
    def resolve_builtin_var(self, var_name: str) -> Optional[str]:
        """Resolve a built-in variable to its tool-specific value.
        
        Args:
            var_name: Variable name without $ prefix (e.g., 'INSTDIR')
            
        Returns:
            Tool-specific variable string, or None if not found
        """
        var_def = self.builtin_vars.get(var_name)
        if var_def is None:
            return None
        
        try:
            return var_def.get_value(self.target_tool)
        except ValueError:
            return None
    
    def add_custom_variable(self, name: str, value: str):
        """Add a custom user-defined variable.
        
        Args:
            name: Variable name
            value: Variable value (can contain references to other variables)
        """
        self.custom_vars[name] = value
    
    def get_custom_variable(self, name: str) -> Optional[str]:
        """Get a custom variable value.
        
        Args:
            name: Variable name
            
        Returns:
            Variable value, or None if not found
        """
        return self.custom_vars.get(name)
    
    def validate_variable(self, var_name: str, strict: bool = False) -> bool:
        """Check if a variable is known (built-in or custom).
        
        Args:
            var_name: Variable name to check
            strict: If True, raise exception for unknown variables
            
        Returns:
            True if variable is known, False otherwise
            
        Raises:
            ValueError: If strict=True and variable is unknown
        """
        is_known = var_name in self.builtin_vars or var_name in self.custom_vars
        
        if not is_known and strict:
            raise ValueError(
                f"Unknown variable: ${var_name}. "
                f"Available built-in variables: {', '.join(sorted(self.builtin_vars.keys()))}"
            )
        
        return is_known

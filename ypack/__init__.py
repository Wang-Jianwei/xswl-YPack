"""
xswl-YPack — A lightweight Windows packaging tool.
Converts YAML configurations into installer scripts (NSIS, WIX, Inno Setup, …).
"""

__version__ = "0.2.0"

from .config import PackageConfig
from .converters import YamlToNsisConverter, get_converter_class

__all__ = [
    "PackageConfig",
    "YamlToNsisConverter",
    "get_converter_class",
    "__version__",
]

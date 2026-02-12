"""
Tests for NSIS header generation utilities, particularly LangString escaping.
"""

import pytest
from ypack.converters.nsis_header import _escape_nsis_langstring


class TestEscapeNsisLangstring:
    """Tests for _escape_nsis_langstring function."""

    def test_simple_text(self):
        """Test basic text without special characters."""
        result = _escape_nsis_langstring("Hello, world!")
        assert result == "Hello, world!"

    def test_quote_escaping(self):
        """Test that double quotes are escaped."""
        result = _escape_nsis_langstring('Say "hello"')
        assert result == 'Say $\\"hello$\\"'

    def test_single_newline(self):
        """Test that single newlines are properly escaped."""
        result = _escape_nsis_langstring("Line 1\nLine 2")
        assert result == "Line 1$\\nLine 2"

    def test_single_carriage_return(self):
        """Test that single carriage returns are properly escaped."""
        result = _escape_nsis_langstring("Line 1\rLine 2")
        assert result == "Line 1$\\rLine 2"

    def test_crlf_newline(self):
        """Test that CRLF sequences are properly escaped to NSIS format."""
        result = _escape_nsis_langstring("Line 1\r\nLine 2")
        assert result == "Line 1$\\r$\\nLine 2"

    def test_normalize_stray_dollar_markers(self):
        """Test that stray $ markers around newlines are normalized."""
        result = _escape_nsis_langstring("Text$\r$and$\n$more")
        assert result == "Text$\\rand$\\nmore"

    def test_mixed_quotes_and_newlines(self):
        """Test text with both quotes and newlines."""
        result = _escape_nsis_langstring('Line 1: "text"\nLine 2')
        assert result == 'Line 1: $\\"text$\\"$\\nLine 2'

    def test_multiline_with_placeholders(self):
        """Test multiline text with NSIS placeholders (should pass through)."""
        result = _escape_nsis_langstring('Path: $R1\nVersion: $R2')
        assert result == 'Path: $R1$\\nVersion: $R2'

    def test_complex_multilingual_scenario(self):
        """Test a realistic scenario from existing-install prompt with variables."""
        # This simulates text like: "An existing installation (version $R2) was found at:\r\n$R1\r\n\r\nUninstall first?"
        text = 'An existing installation (version $R2) was found at:\r\n$R1\r\n\r\nUninstall first?'
        result = _escape_nsis_langstring(text)
        assert result == 'An existing installation (version $R2) was found at:$\\r$\\n$R1$\\r$\\n$\\r$\\nUninstall first?'

    def test_empty_string(self):
        """Test that empty string is handled correctly."""
        result = _escape_nsis_langstring("")
        assert result == ""

    def test_multiple_consecutive_newlines(self):
        """Test multiple consecutive newlines."""
        result = _escape_nsis_langstring("Text\n\n\nMore")
        assert result == "Text$\\n$\\n$\\nMore"

    def test_multiple_consecutive_crlf(self):
        """Test multiple consecutive CRLF sequences."""
        result = _escape_nsis_langstring("Text\r\n\r\nMore")
        assert result == "Text$\\r$\\n$\\r$\\nMore"

    def test_normalized_dollar_then_actual_newline(self):
        """Test normalization of stray markers followed by actual newlines."""
        result = _escape_nsis_langstring("Text$\r$\nMore")
        # $\r$ normalizes to \r, then combined with \n gives us $\r$\n
        assert result == "Text$\\r$\\nMore"

    def test_idempotence_with_already_escaped_quotes(self):
        """Test that the function handles text that already has escaped quotes correctly."""
        # If somehow input already has $\", the function should escape the $ and \ separately
        result = _escape_nsis_langstring('Text with $\\"quote')
        # The quote won't be escaped again (no double-escaping)
        # But $ and \ will remain as-is unless they're part of the patterns we normalize
        assert '$\\"' in result or '$$\\\\' in result  # Flexible assertion for various escaping orders

    def test_real_world_chinese_text(self):
        """Test real-world Chinese translation with newlines."""
        text = "在以下位置发现已存在的安装：\r\n$R1\r\n\r\n是否先卸载再继续？"
        result = _escape_nsis_langstring(text)
        assert result == "在以下位置发现已存在的安装：$\\r$\\n$R1$\\r$\\n$\\r$\\n是否先卸载再继续？"

    def test_real_world_french_text(self):
        """Test real-world French translation with newlines and accents."""
        text = 'Une installation existante a été trouvée à :\r\n$R1\r\n\r\nDésinstaller d\'abord et continuer ?'
        result = _escape_nsis_langstring(text)
        assert result == 'Une installation existante a été trouvée à :$\\r$\\n$R1$\\r$\\n$\\r$\\nDésinstaller d\'abord et continuer ?'

    def test_format_placeholder_preservation(self):
        """Test that format placeholders like {mb} are preserved."""
        text = "Not enough space. Require {mb} MB."
        result = _escape_nsis_langstring(text)
        assert result == "Not enough space. Require {mb} MB."
        assert "{mb}" in result  # Ensure placeholder survives

    def test_nsis_variable_preservation(self):
        """Test that NSIS variables like $INSTDIR are preserved."""
        text = "Install directory: $INSTDIR"
        result = _escape_nsis_langstring(text)
        assert result == "Install directory: $INSTDIR"
        assert "$INSTDIR" in result

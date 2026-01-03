"""
Tests for gensenses functionality using unittest framework.
"""
import unittest
from typing import Any

from gensenses import process_snc_list, extract_dif_text


class TestGensenses(unittest.TestCase):
    """Test cases for gensenses functionality."""

    def test_extract_dif_text_simple(self):
        """Test extracting text from a simple dif element."""
        dif_data = {
            "content": [
                {"text": "  This is a definition  "},
                {"text": "  with multiple parts.  "}
            ]
        }
        result = extract_dif_text(dif_data, None, {})
        self.assertEqual(result, "This is a definition with multiple parts.")

    def test_extract_dif_text_with_tld(self):
        """Test extracting dif with tld replacement."""
        dif_data = {
            "content": [
                {"text": "A member of the "},
                {"tld": {"lit": "", "var": ""}},
                {"text": " people"}
            ]
        }
        result = extract_dif_text(dif_data, "aleut", {})
        self.assertEqual(result, "A member of the aleut people.")

    def test_extract_dif_text_with_tld_lit(self):
        """Test extracting dif with tld having lit attribute."""
        dif_data = {
            "content": [
                {"text": "The "},
                {"tld": {"lit": "A", "var": ""}},
                {"text": " islands"}
            ]
        }
        result = extract_dif_text(dif_data, "aleut", {})
        self.assertEqual(result, "The Aleut islands.")

    def test_extract_dif_text_empty(self):
        """Test extracting from empty dif."""
        dif_data: dict[str, Any] = {}
        result = extract_dif_text(dif_data, None, {})
        self.assertEqual(result, "")

    def test_process_snc_list_single(self):
        """Test processing a single snc."""
        snc_list = [
            {
                "snc": {
                    "content": [
                        {
                            "dif": {
                                "content": [
                                    {"text": "First sense"}
                                ]
                            }
                        }
                    ]
                }
            }
        ]
        result = process_snc_list(snc_list, None, {})
        self.assertEqual(result, {"1": "First sense."})

    def test_process_snc_list_multiple(self):
        """Test processing multiple snc elements."""
        snc_list = [
            {
                "snc": {
                    "content": [
                        {
                            "dif": {
                                "content": [
                                    {"text": "First sense"}
                                ]
                            }
                        }
                    ]
                }
            },
            {
                "snc": {
                    "content": [
                        {
                            "dif": {
                                "content": [
                                    {"text": "Second sense"}
                                ]
                            }
                        }
                    ]
                }
            }
        ]
        result = process_snc_list(snc_list, None, {})
        self.assertEqual(result, {"1": "First sense.", "2": "Second sense."})

    def test_process_snc_list_nested(self):
        """Test processing nested snc/subsnc elements."""
        snc_list = [
            {
                "snc": {
                    "content": [
                        {
                            "dif": {
                                "content": [
                                    {"text": "First sense"}
                                ]
                            }
                        },
                        {
                            "snc": {
                                "content": [
                                    {
                                        "dif": {
                                            "content": [
                                                {"text": "First subsense"}
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        {
                            "snc": {
                                "content": [
                                    {
                                        "dif": {
                                            "content": [
                                                {"text": "Second subsense"}
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        ]
        result = process_snc_list(snc_list, None, {})
        expected = {
            "1": "First sense.",
            "1.1": "First subsense.",
            "1.2": "Second subsense."
        }
        self.assertEqual(result, expected)

    def test_process_snc_list_deeply_nested(self):
        """Test processing deeply nested snc elements."""
        snc_list = [
            {
                "snc": {
                    "content": [
                        {
                            "dif": {
                                "content": [
                                    {"text": "First sense"}
                                ]
                            }
                        },
                        {
                            "snc": {
                                "content": [
                                    {
                                        "dif": {
                                            "content": [
                                                {"text": "Subsense 1.1"}
                                            ]
                                        }
                                    },
                                    {
                                        "snc": {
                                            "content": [
                                                {
                                                    "dif": {
                                                        "content": [
                                                            {"text": "Subsense 1.1.1"}
                                                        ]
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        ]
        result = process_snc_list(snc_list, None, {})
        expected = {
            "1": "First sense.",
            "1.1": "Subsense 1.1.",
            "1.1.1": "Subsense 1.1.1."
        }
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()

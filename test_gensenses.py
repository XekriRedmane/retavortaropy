"""
Tests for gensenses functionality using unittest framework.
"""
import unittest

from lxml import etree

from gensenses import process_snc_list, extract_dif_text


class TestGensenses(unittest.TestCase):
    """Test cases for gensenses functionality."""

    def test_extract_dif_text_simple(self):
        """Test extracting text from a simple dif element."""
        dif_el = etree.fromstring(
            "<dif>  This is a definition    with multiple parts.  </dif>"
        )
        result = extract_dif_text(dif_el, None, {})
        self.assertEqual(result, "This is a definition with multiple parts.")

    def test_extract_dif_text_with_tld(self):
        """Test extracting dif with tld replacement."""
        dif_el = etree.fromstring(
            "<dif>A member of the <tld/> people</dif>"
        )
        result = extract_dif_text(dif_el, "aleut", {})
        self.assertEqual(result, "A member of the aleut people.")

    def test_extract_dif_text_with_tld_lit(self):
        """Test extracting dif with tld having lit attribute."""
        dif_el = etree.fromstring(
            '<dif>The <tld lit="A"/> islands</dif>'
        )
        result = extract_dif_text(dif_el, "aleut", {})
        self.assertEqual(result, "The Aleut islands.")

    def test_extract_dif_text_empty(self):
        """Test extracting from empty dif."""
        dif_el = etree.fromstring("<dif/>")
        result = extract_dif_text(dif_el, None, {})
        self.assertEqual(result, "")

    def test_process_snc_list_single(self):
        """Test processing a single snc."""
        snc = etree.fromstring(
            "<snc><dif>First sense</dif></snc>"
        )
        result = process_snc_list([snc], None, {})
        self.assertEqual(result, {"1": "First sense."})

    def test_process_snc_list_multiple(self):
        """Test processing multiple snc elements."""
        snc1 = etree.fromstring("<snc><dif>First sense</dif></snc>")
        snc2 = etree.fromstring("<snc><dif>Second sense</dif></snc>")
        result = process_snc_list([snc1, snc2], None, {})
        self.assertEqual(result, {"1": "First sense.", "2": "Second sense."})

    def test_process_snc_list_nested(self):
        """Test processing nested snc/subsnc elements."""
        parent = etree.fromstring(
            "<snc>"
            "<dif>First sense</dif>"
            "<snc><dif>First subsense</dif></snc>"
            "<snc><dif>Second subsense</dif></snc>"
            "</snc>"
        )
        result = process_snc_list([parent], None, {})
        expected = {
            "1": "First sense.",
            "1.1": "First subsense.",
            "1.2": "Second subsense."
        }
        self.assertEqual(result, expected)

    def test_process_snc_list_deeply_nested(self):
        """Test processing deeply nested snc elements."""
        parent = etree.fromstring(
            "<snc>"
            "<dif>First sense</dif>"
            "<snc>"
            "<dif>Subsense 1.1</dif>"
            "<snc><dif>Subsense 1.1.1</dif></snc>"
            "</snc>"
            "</snc>"
        )
        result = process_snc_list([parent], None, {})
        expected = {
            "1": "First sense.",
            "1.1": "Subsense 1.1.",
            "1.1.1": "Subsense 1.1.1."
        }
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()

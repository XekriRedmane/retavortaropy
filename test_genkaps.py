"""
Tests for genkaps functionality using unittest framework.
"""
import pathlib
import sys
import unittest
from lxml import etree
from lxml.sax import saxify
from jsonpath_ng import parse

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

from retavortaropy.main import DTDResolver, RevoContentHandler
from retavortaropy import utils
from genkaps import get_json_kap_text, get_variant_rads


class TestGenkaps(unittest.TestCase):
    """Test cases for genkaps functionality."""

    def test_simple_kap(self):
        """Test simple kap with tld and text."""
        kap_dict = {
            "content": [
                {"tld": {"lit": "", "var": ""}},
                {"text": "a"}
            ]
        }
        result = get_json_kap_text(kap_dict, "absolut")
        self.assertEqual(result, ["absoluta"])

    def test_whitespace_only_text_nodes(self):
        """Test that whitespace-only text nodes are ignored."""
        kap_dict = {
            "content": [
                {"text": "\n    "},
                {"tld": {"lit": "", "var": ""}},
                {"text": "e"},
                {"text": "\n  "}
            ]
        }
        result = get_json_kap_text(kap_dict, "abrupt")
        self.assertEqual(result, ["abrupte"])

    def test_a_volvita_spacing(self):
        """Test that spacing between words is preserved correctly."""
        kap_dict = {
            "content": [
                {"tld": {"lit": "", "var": ""}},
                {"text": " volvita"},
                {"text": "\n    "},
                {"text": "\n  "}
            ]
        }
        result = get_json_kap_text(kap_dict, "a")
        self.assertEqual(result, ["a volvita"])

    def test_abrupte_real_file(self):
        """Test extraction from abrupt.xml file."""
        xml_path = pathlib.Path("F:/revo-fonto/revo/abrupt.xml")
        if not xml_path.exists():
            self.skipTest("abrupt.xml not found")

        xml_parser = etree.XMLParser(load_dtd=True, resolve_entities=True)
        xml_parser.resolvers.add(DTDResolver())
        with open(xml_path, "r", encoding="UTF-8") as f:
            tree = etree.parse(f, parser=xml_parser)

        handler = RevoContentHandler()
        saxify(tree, handler)
        root_dict = handler.root.json_encode()
        rad_text = utils.json_get_closest_rad_text(root_dict)

        jsonpath_expression = parse('$..drv')
        matches = jsonpath_expression.find(root_dict)

        found = False
        for match in matches:
            kap_wrapper = match.value.get('kap')
            if kap_wrapper and 'kap' in kap_wrapper:
                kap_texts = get_json_kap_text(kap_wrapper['kap'], rad_text)
                if "abrupte" in kap_texts:
                    for kap_text in kap_texts:
                        self.assertNotIn('\n', kap_text, f"Found newline in '{kap_text}'")
                    found = True
                    break
        self.assertTrue(found, "Expected to find 'abrupte' in kap texts")

    def test_a_volvita_real_file(self):
        """Test extraction from a1.xml file."""
        xml_path = pathlib.Path("F:/revo-fonto/revo/a1.xml")
        if not xml_path.exists():
            self.skipTest("a1.xml not found")

        xml_parser = etree.XMLParser(load_dtd=True, resolve_entities=True)
        xml_parser.resolvers.add(DTDResolver())
        with open(xml_path, "r", encoding="UTF-8") as f:
            tree = etree.parse(f, parser=xml_parser)

        handler = RevoContentHandler()
        saxify(tree, handler)
        root_dict = handler.root.json_encode()
        rad_text = utils.json_get_closest_rad_text(root_dict)

        jsonpath_expression = parse('$..drv')
        matches = jsonpath_expression.find(root_dict)

        found = False
        for match in matches:
            kap_wrapper = match.value.get('kap')
            if kap_wrapper and 'kap' in kap_wrapper:
                kap_texts = get_json_kap_text(kap_wrapper['kap'], rad_text)
                for kap_text in kap_texts:
                    if "volvita" in kap_text:
                        self.assertEqual(kap_text, "a volvita")
                        self.assertNotIn('\n', kap_text, f"Found newline in '{kap_text}'")
                        found = True
                        break
                if found:
                    break
        self.assertTrue(found, "Expected to find 'a volvita' in kap texts")


if __name__ == "__main__":
    unittest.main()

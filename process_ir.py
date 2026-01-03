"""
Script to process all XML files in a directory, convert to JSON, and extract filtered drv kaps.
"""

import argparse
import pathlib
from typing import Any
from lxml import etree
from lxml.sax import saxify
from jsonpath_ng import parse
from tqdm import tqdm

from retavortaropy.main import DTDResolver, RevoContentHandler
from retavortaropy import utils

# Ensure we have the necessary classes available for the handler
from retavortaropy.data import vortaro

FAK = "MIN"


def get_json_kap_text(kap_dict: dict[str, Any], rad_text: str | None) -> str:
    """
    Reconstructs the kap text from its JSON representation, processing tld.
    Iterates through content in order to preserve spacing.
    """
    if not kap_dict:
        return ""

    content = kap_dict.get("content", [])
    if not content:
        return ""

    parts = []

    for item in content:
        # Each item is a dict with one key indicating the element type
        if "text" in item:
            # Plain text node - preserve it exactly as is (including spaces)
            parts.append(item["text"])
        elif "tld" in item:
            # Tilde replacement
            if rad_text is not None:
                tld_data = item["tld"]
                lit = tld_data.get("lit", "")
                if lit:
                    parts.append(lit + rad_text[1:])
                else:
                    parts.append(rad_text)
        elif "rad" in item:
            # Rad element
            rad_data = item["rad"]
            if "text" in rad_data:
                parts.append(rad_data["text"])

    return "".join(parts)


def get_simple_text_content(element_dict: dict[str, Any]) -> str:
    """
    Extracts simple text content from an element dictionary (like Uzo).
    """
    parts = []
    content = element_dict.get("content", [])
    for item in content:
        for k, v in item.items():
            if k == "text":
                if isinstance(v, str):
                    parts.append(v)
            elif isinstance(v, dict) and "text" in v:
                parts.append(v["text"])
    return "".join(parts)


def process_file(xml_path: pathlib.Path, parser: etree.XMLParser) -> list[str]:
    """
    Processes a single XML file and returns a list of formatted result strings.
    """
    file_results = []
    try:
        with open(xml_path, "r", encoding="UTF-8") as f:
            tree = etree.parse(f, parser=parser)

        handler = RevoContentHandler()
        saxify(tree, handler)
        root = handler.root
        root_dict = root.json_encode()

        rad_text = utils.json_get_closest_rad_text(root_dict)

        jsonpath_expression = parse("$..drv")
        matches = jsonpath_expression.find(root_dict)

        drv_kaps = []
        for match in matches:
            drv_data = match.value
            kap_wrapper = drv_data.get("kap")
            if kap_wrapper and "kap" in kap_wrapper:
                kap_inner = kap_wrapper["kap"]
                kap_text = get_json_kap_text(kap_inner, rad_text)
                drv_kaps.append((kap_text, drv_data))
            else:
                drv_kaps.append(("(No Kap)", drv_data))

        trd_expr = parse("$..trd")
        trdgrp_expr = parse("$..trdgrp")
        uzo_expr = parse("$..uzo")

        for k, drv_data in drv_kaps:
            match_filter = False
            for match in uzo_expr.find(drv_data):
                uzo_val = match.value
                if uzo_val.get("tip") == "fak":
                    content_text = get_simple_text_content(uzo_val)
                    if FAK in content_text:
                        match_filter = True
                        break

            if not match_filter:
                continue

            has_en = False
            for match in trd_expr.find(drv_data):
                if match.value.get("lng") == "en":
                    has_en = True
                    break

            if not has_en:
                for match in trdgrp_expr.find(drv_data):
                    if match.value.get("lng") == "en":
                        has_en = True
                        break

            status_icon = "✅" if has_en else "❌"
            if not has_en:
                file_results.append(f"{status_icon} {k}")

    except Exception as e:
        # We might want to log errors but not stop the entire process
        # For now, just ignore or print to stderr if needed, but keeping output clean
        pass

    return file_results


def main():
    parser = argparse.ArgumentParser(description="Process Revo XML files.")
    parser.add_argument(
        "directory",
        nargs="?",
        default="f:/revo-fonto/revo",
        help="Directory containing XML files",
    )
    args = parser.parse_args()

    dir_path = pathlib.Path(args.directory)
    if not dir_path.exists() or not dir_path.is_dir():
        print(f"Error: Directory {dir_path} not found.")
        return

    xml_files = list(dir_path.glob("*.xml"))

    # Initialize parser once
    xml_parser = etree.XMLParser(load_dtd=True, resolve_entities=True)
    xml_parser.resolvers.add(DTDResolver())

    all_results = []

    for xml_file in tqdm(xml_files, desc="Processing XML files", unit="file"):
        results = process_file(xml_file, xml_parser)
        all_results.extend(results)

    for res in all_results:
        print(res)


if __name__ == "__main__":
    main()

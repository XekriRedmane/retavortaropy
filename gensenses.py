"""
Command line tool to extract sense definitions (dif) from drv and subdrv elements.
Creates a dictionary mapping sense numbers to their definitions.
"""

import argparse
import json
import pathlib
from typing import Any

from lxml import etree
from lxml.sax import saxify
from jsonpath_ng import parse
from tqdm import tqdm

from retavortaropy.xmlparse import DTDResolver, RevoContentHandler


def extract_dif_text(dif_data: dict[str, Any]) -> str:
    """
    Extract text content from a dif element.

    Args:
        dif_data: The dif dictionary from JSON

    Returns:
        The text content of the dif element
    """
    if not dif_data or "content" not in dif_data:
        return ""

    parts: list[str] = []
    content = dif_data.get("content", [])

    for item in content:
        if "text" in item:
            text = item["text"]
            if text.strip():
                parts.append(text.strip())

    return " ".join(parts)


def process_snc_list(snc_list: list[dict[str, Any]], base_num: str = "") -> dict[str, str]:
    """
    Process a list of snc/subsnc elements and extract their definitions.

    Args:
        snc_list: List of snc dictionaries
        base_num: Base number for this level (empty for top level)

    Returns:
        Dictionary mapping sense numbers to definitions
    """
    result: dict[str, str] = {}
    snc_count = 0

    for item in snc_list:
        if "snc" in item:
            snc_count += 1
            snc_data = item["snc"]

            # Determine the sense number
            if base_num:
                sense_num = f"{base_num}.{snc_count}"
            else:
                sense_num = str(snc_count)

            # Extract the dif from this snc
            if "content" in snc_data:
                for content_item in snc_data["content"]:
                    if "dif" in content_item:
                        dif_text = extract_dif_text(content_item["dif"])
                        if dif_text:
                            result[sense_num] = dif_text
                        break

            # Process any subsnc elements recursively
            if "content" in snc_data:
                subsnc_list = [item for item in snc_data["content"] if "snc" in item]
                if subsnc_list:
                    sub_results = process_snc_list(subsnc_list, sense_num)
                    result.update(sub_results)

    return result


def process_drv_or_subdrv(drv_data: dict[str, Any]) -> dict[str, str]:
    """
    Process a drv or subdrv element and extract sense definitions.

    Args:
        drv_data: The drv or subdrv dictionary from JSON

    Returns:
        Dictionary mapping sense numbers to definitions
    """
    if not drv_data or "content" not in drv_data:
        return {}

    content = drv_data.get("content", [])
    snc_list = [item for item in content if "snc" in item]

    return process_snc_list(snc_list)


def process_file(xml_path: pathlib.Path, parser: etree.XMLParser) -> dict[str, dict[str, str]]:
    """
    Process a single XML file and extract all drv/subdrv sense definitions.

    Args:
        xml_path: Path to the XML file to process.
        parser: The XML parser to use.

    Returns:
        Dictionary mapping drv mrk to sense dictionaries
    """
    drv_senses: dict[str, dict[str, str]] = {}

    try:
        with open(xml_path, "r", encoding="UTF-8") as f:
            tree = etree.parse(f, parser=parser)

        handler = RevoContentHandler()
        saxify(tree, handler)
        root = handler.root
        root_dict: dict[str, Any] = root.json_encode()

        # Find all drv elements
        jsonpath_expression = parse("$..drv")
        matches = jsonpath_expression.find(root_dict)

        for match in matches:
            drv_data = match.value
            mrk = drv_data.get("mrk", "")

            if mrk:
                senses = process_drv_or_subdrv(drv_data)
                if senses:
                    drv_senses[mrk] = senses

        # Find all subdrv elements
        jsonpath_expression = parse("$..subdrv")
        matches = jsonpath_expression.find(root_dict)

        for match in matches:
            subdrv_data = match.value
            mrk = subdrv_data.get("mrk", "")

            if mrk:
                senses = process_drv_or_subdrv(subdrv_data)
                if senses:
                    drv_senses[mrk] = senses

    except Exception as e:
        print(f"Error processing {xml_path.name}: {e}")

    return drv_senses


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract sense definitions from Revo XML files."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="f:/revo-fonto/revo",
        help="Directory containing XML files or single XML file",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="sense_dictionary.json",
        help="Output JSON file path (default: sense_dictionary.json)",
    )
    args = parser.parse_args()

    input_path = pathlib.Path(args.path)
    if not input_path.exists():
        print(f"Error: Path {input_path} not found.")
        return

    # Check if it's a file or directory
    if input_path.is_file():
        xml_files = [input_path]
    elif input_path.is_dir():
        xml_files = list(input_path.glob("*.xml"))
    else:
        print(f"Error: {input_path} is neither a file nor a directory.")
        return

    if not xml_files:
        print(f"No XML files found in {input_path}")
        return

    # Initialize parser once
    xml_parser = etree.XMLParser(load_dtd=True, resolve_entities=True)
    xml_parser.resolvers.add(DTDResolver())

    # Dictionary to store all drv mrk -> sense mappings
    all_senses: dict[str, dict[str, str]] = {}

    for xml_file in tqdm(xml_files, desc="Processing XML files", unit="file"):
        file_senses = process_file(xml_file, xml_parser)
        all_senses.update(file_senses)

    # Write results to JSON file
    output_path = pathlib.Path(args.output)
    with open(output_path, "w", encoding="UTF-8") as f:
        json.dump(all_senses, f, ensure_ascii=False, indent=2)

    print(f"\nExtracted senses from {len(all_senses)} drv/subdrv elements")
    print(f"Results written to {output_path}")


if __name__ == "__main__":
    main()

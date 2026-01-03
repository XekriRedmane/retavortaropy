"""
Command line tool to extract rad values from all XML files in a directory.
Creates a dictionary mapping rad text to XML file paths.
Includes both base rads and variant rads.
"""

import argparse
import json
import pathlib
from typing import Any
from lxml import etree
from lxml.sax import saxify
from tqdm import tqdm

from retavortaropy.xmlparse import DTDResolver, RevoContentHandler


def get_rads_from_art(root_dict: dict[str, Any]) -> list[str]:
    """
    Extract all rad texts from the top-level art/kap element.
    Includes both base rad and variant rads.

    Args:
        root_dict: The root dictionary from JSON

    Returns:
        List of rad texts (base rad + any variant rads)
    """
    rads = []

    try:
        vortaro = root_dict.get("vortaro", {})
        content = vortaro.get("content", [])

        for item in content:
            if "art" in item:
                art_data = item["art"]
                kap_wrapper = art_data.get("kap", {})
                kap_data = kap_wrapper.get("kap", {})
                kap_content = kap_data.get("content", [])

                for kap_item in kap_content:
                    if "rad" in kap_item:
                        rad_data = kap_item["rad"]
                        var = rad_data.get("var", "")
                        text = rad_data.get("text", "")
                        # Include base rad (no var attribute or empty var)
                        if not var and text:
                            rads.append(text)
                    elif "var" in kap_item:
                        # Extract variant rad from var/kap/kap/content
                        var_data = kap_item["var"]
                        if "kap" in var_data:
                            var_kap_wrapper = var_data["kap"]
                            if "kap" in var_kap_wrapper:
                                var_kap = var_kap_wrapper["kap"]
                                var_content = var_kap.get("content", [])
                                for var_item in var_content:
                                    if "rad" in var_item:
                                        rad_data = var_item["rad"]
                                        text = rad_data.get("text", "")
                                        if text:
                                            rads.append(text)
    except Exception:
        pass

    return rads


def process_file(xml_path: pathlib.Path, parser: etree.XMLParser) -> dict[str, str]:
    """
    Processes a single XML file and extracts all rad texts.

    Args:
        xml_path: Path to the XML file to process.
        parser: The XML parser to use.

    Returns:
        Dictionary mapping rad texts to file path
    """
    rad_to_file = {}

    try:
        with open(xml_path, "r", encoding="UTF-8") as f:
            tree = etree.parse(f, parser=parser)

        handler = RevoContentHandler()
        saxify(tree, handler)
        root = handler.root
        root_dict = root.json_encode()

        rad_texts = get_rads_from_art(root_dict)
        for rad_text in rad_texts:
            rad_to_file[rad_text] = xml_path.stem

    except Exception as e:
        print(f"Error processing {xml_path.name}: {e}")

    return rad_to_file


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract rad values from Revo XML files and create a rad-to-file dictionary."
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
        default="rad_dictionary.json",
        help="Output JSON file path (default: rad_dictionary.json)",
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

    # Dictionary to store all rad -> file mappings
    all_rads = {}
    files_without_rad = []

    for xml_file in tqdm(xml_files, desc="Processing XML files", unit="file"):
        file_rads = process_file(xml_file, xml_parser)
        if file_rads:
            all_rads.update(file_rads)
        else:
            files_without_rad.append(str(xml_file))

    # Write results to JSON file
    output_path = pathlib.Path(args.output)
    with open(output_path, "w", encoding="UTF-8") as f:
        json.dump(all_rads, f, ensure_ascii=False, indent=2)

    print(f"\nExtracted {len(all_rads)} rad entries")
    if files_without_rad:
        print(f"Warning: {len(files_without_rad)} files had no rad element")
    print(f"Results written to {output_path}")


if __name__ == "__main__":
    main()

"""
Command line tool to extract sense definitions (dif) from drv and subdrv elements.
Creates a dictionary mapping kap text to sense dictionaries.
"""

import argparse
import json
import pathlib
import sys
from typing import Any

from lxml import etree
from lxml.sax import saxify
from jsonpath_ng import parse
from tqdm import tqdm

from retavortaropy.xmlparse import DTDResolver, RevoContentHandler
from retavortaropy import utils
from config import get_revo_path
from genkaps import get_json_kap_text, get_variant_rads


def extract_dif_text(
    dif_data: dict[str, Any], rad_text: str | None, variant_rads: dict[str, str]
) -> str:
    """
    Extract text content from a dif element, replacing tld with rad.

    Args:
        dif_data: The dif dictionary from JSON
        rad_text: The base rad text for tld replacement
        variant_rads: Dictionary mapping var attributes to variant rad texts

    Returns:
        The text content of the dif element with tld replaced
    """
    if not dif_data or "content" not in dif_data:
        return ""

    parts: list[str] = []
    content = dif_data.get("content", [])

    for item in content:
        if "text" in item:
            text = item["text"]
            parts.append(text)
        elif "tld" in item:
            if rad_text is not None:
                tld_data = item["tld"]
                lit = tld_data.get("lit", "")
                var = tld_data.get("var", "")

                # Use variant rad if var attribute is present
                if var and var in variant_rads:
                    rad_to_use = variant_rads[var]
                else:
                    rad_to_use = rad_text

                if lit:
                    parts.append(lit + rad_to_use[1:])
                else:
                    parts.append(rad_to_use)
        elif "ref" in item:
            # Extract text from ref elements, processing tld within them
            ref_data = item["ref"]
            ref_content = ref_data.get("content", [])
            for ref_item in ref_content:
                if "text" in ref_item:
                    parts.append(ref_item["text"])
                elif "tld" in ref_item:
                    # Process tld inside ref elements
                    if rad_text is not None:
                        tld_data = ref_item["tld"]
                        lit = tld_data.get("lit", "")
                        var = tld_data.get("var", "")

                        # Use variant rad if var attribute is present
                        if var and var in variant_rads:
                            rad_to_use = variant_rads[var]
                        else:
                            rad_to_use = rad_text

                        if lit:
                            parts.append(lit + rad_to_use[1:])
                        else:
                            parts.append(rad_to_use)
        elif "refgrp" in item:
            # Extract text from refgrp elements (groups of references)
            refgrp_data = item["refgrp"]
            refgrp_content = refgrp_data.get("content", [])
            for refgrp_item in refgrp_content:
                if "text" in refgrp_item:
                    parts.append(refgrp_item["text"])
                elif "ref" in refgrp_item:
                    # Process ref elements within refgrp
                    ref_data = refgrp_item["ref"]
                    ref_content = ref_data.get("content", [])
                    for ref_item in ref_content:
                        if "text" in ref_item:
                            parts.append(ref_item["text"])
                        elif "tld" in ref_item:
                            # Process tld inside ref elements
                            if rad_text is not None:
                                tld_data = ref_item["tld"]
                                lit = tld_data.get("lit", "")
                                var = tld_data.get("var", "")

                                # Use variant rad if var attribute is present
                                if var and var in variant_rads:
                                    rad_to_use = variant_rads[var]
                                else:
                                    rad_to_use = rad_text

                                if lit:
                                    parts.append(lit + rad_to_use[1:])
                                else:
                                    parts.append(rad_to_use)

    # Join all parts and normalize whitespace
    result = "".join(parts)
    # Replace multiple spaces/newlines with single space and strip
    result = " ".join(result.split())

    # Ensure proper ending punctuation
    if result.endswith(":"):
        # Replace trailing colon with period
        result = result[:-1] + "."
    elif result and not result[-1] in ".!?;":
        # Add period if no ending punctuation
        result = result + "."

    return result


def process_snc_list(
    snc_list: list[dict[str, Any]],
    rad_text: str | None,
    variant_rads: dict[str, str],
    base_num: str = "",
) -> dict[str, str]:
    """
    Process a list of snc/subsnc elements and extract their definitions.

    Args:
        snc_list: List of snc dictionaries
        rad_text: The base rad text for tld replacement
        variant_rads: Dictionary mapping var attributes to variant rad texts
        base_num: Base number for this level (empty for top level)

    Returns:
        Dictionary mapping sense numbers to definitions
    """
    result: dict[str, str] = {}
    snc_count = 0

    for item in snc_list:
        # Handle both snc and subsnc elements
        if "snc" in item or "subsnc" in item:
            snc_count += 1
            snc_data = item.get("snc") or item.get("subsnc")

            # Determine the sense number
            if base_num:
                sense_num = f"{base_num}.{snc_count}"
            else:
                sense_num = str(snc_count)

            # Extract the dif from this snc/subsnc
            if "content" in snc_data:
                for content_item in snc_data["content"]:
                    if "dif" in content_item:
                        dif_text = extract_dif_text(
                            content_item["dif"], rad_text, variant_rads
                        )
                        if dif_text:
                            result[sense_num] = dif_text
                        break
                    elif "refgrp" in content_item:
                        # Check if this is a refgrp with tip="dif"
                        refgrp_data = content_item["refgrp"]
                        if refgrp_data.get("tip") == "dif":
                            # Treat this refgrp as a definition
                            dif_data = {"content": [content_item]}
                            dif_text = extract_dif_text(dif_data, rad_text, variant_rads)
                            if dif_text:
                                result[sense_num] = dif_text
                            break
                    elif "ref" in content_item:
                        # Check if this is a ref with tip="dif"
                        ref_data = content_item["ref"]
                        if ref_data.get("tip") == "dif":
                            # Treat this ref as a definition
                            dif_data = {"content": [content_item]}
                            dif_text = extract_dif_text(dif_data, rad_text, variant_rads)
                            if dif_text:
                                result[sense_num] = dif_text
                            break

            # Process any nested snc/subsnc elements recursively
            if "content" in snc_data:
                nested_list = [
                    item for item in snc_data["content"]
                    if "snc" in item or "subsnc" in item
                ]
                if nested_list:
                    sub_results = process_snc_list(
                        nested_list, rad_text, variant_rads, sense_num
                    )
                    result.update(sub_results)

    return result


def process_drv_or_subdrv(
    drv_data: dict[str, Any], rad_text: str | None, variant_rads: dict[str, str]
) -> dict[str, str]:
    """
    Process a drv or subdrv element and extract sense definitions.

    Args:
        drv_data: The drv or subdrv dictionary from JSON
        rad_text: The base rad text for tld replacement
        variant_rads: Dictionary mapping var attributes to variant rad texts

    Returns:
        Dictionary mapping sense numbers to definitions
    """
    if not drv_data or "content" not in drv_data:
        return {}

    content = drv_data.get("content", [])
    snc_list = [item for item in content if "snc" in item]

    return process_snc_list(snc_list, rad_text, variant_rads)


def process_file(xml_path: pathlib.Path, parser: etree.XMLParser) -> dict[str, dict[str, str]]:
    """
    Process a single XML file and extract all drv/subdrv sense definitions.

    Args:
        xml_path: Path to the XML file to process.
        parser: The XML parser to use.

    Returns:
        Dictionary mapping kap text to sense dictionaries
    """
    drv_senses: dict[str, dict[str, str]] = {}

    try:
        with open(xml_path, "r", encoding="UTF-8") as f:
            tree = etree.parse(f, parser=parser)

        handler = RevoContentHandler()
        saxify(tree, handler)
        root = handler.root
        root_dict: dict[str, Any] = root.json_encode()

        rad_text: str | None = utils.json_get_closest_rad_text(root_dict)
        variant_rads: dict[str, str] = get_variant_rads(root_dict)

        # Find all drv elements
        jsonpath_expression = parse("$..drv")
        matches = jsonpath_expression.find(root_dict)

        for match in matches:
            drv_data = match.value

            # Extract kap text from this drv
            kap_wrapper = drv_data.get("kap")
            if kap_wrapper and "kap" in kap_wrapper:
                kap_inner = kap_wrapper["kap"]
                kap_texts = get_json_kap_text(kap_inner, rad_text, variant_rads)

                # Get senses for this drv
                senses = process_drv_or_subdrv(drv_data, rad_text, variant_rads)

                # Map each kap variant to the same senses
                for kap_text in kap_texts:
                    if kap_text and senses:
                        drv_senses[kap_text] = senses

        # Find all subdrv elements
        jsonpath_expression = parse("$..subdrv")
        matches = jsonpath_expression.find(root_dict)

        for match in matches:
            subdrv_data = match.value

            # Extract kap text from this subdrv
            kap_wrapper = subdrv_data.get("kap")
            if kap_wrapper and "kap" in kap_wrapper:
                kap_inner = kap_wrapper["kap"]
                kap_texts = get_json_kap_text(kap_inner, rad_text, variant_rads)

                # Get senses for this subdrv
                senses = process_drv_or_subdrv(subdrv_data, rad_text, variant_rads)

                # Map each kap variant to the same senses
                for kap_text in kap_texts:
                    if kap_text and senses:
                        drv_senses[kap_text] = senses

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
        default=None,
        help="Directory containing XML files or single XML file",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output JSON file path (default: write to console)",
    )
    args = parser.parse_args()

    if args.path is None:
        revo_path = get_revo_path()
        if revo_path is None:
            print(
                "Error: revo-fonto dictionary not found. "
                "Run 'python download_revo.py' to download it.",
                file=sys.stderr,
            )
            sys.exit(1)
        args.path = str(revo_path)

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

    # Dictionary to store all kap -> sense mappings
    all_senses: dict[str, dict[str, str]] = {}

    # Use tqdm only when writing to a file
    if args.output:
        for xml_file in tqdm(xml_files, desc="Processing XML files", unit="file"):
            file_senses = process_file(xml_file, xml_parser)
            all_senses.update(file_senses)
    else:
        # No progress bar when writing to console
        for xml_file in xml_files:
            file_senses = process_file(xml_file, xml_parser)
            all_senses.update(file_senses)

    # Write results to output file or console
    if args.output:
        output_path = pathlib.Path(args.output)
        with open(output_path, "w", encoding="UTF-8") as f:
            json.dump(all_senses, f, ensure_ascii=False, indent=2)
        print(f"\nExtracted senses for {len(all_senses)} kap entries")
        print(f"Results written to {output_path}")
    else:
        # Write to console with UTF-8 encoding - no other output
        # Reconfigure stdout to use UTF-8 encoding
        sys.stdout.reconfigure(encoding='utf-8')
        json.dump(all_senses, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

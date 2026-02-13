"""
Command line tool to extract sense definitions (dif) from drv and subdrv elements.
Creates a dictionary mapping kap text to sense dictionaries.
"""

import argparse
import json
import pathlib
import sys
import zipfile

from lxml import etree
from tqdm import tqdm

from retavortaropy.xmlparse import DTDResolver
from config import get_revo_path, get_genfiles_path
from genkaps import reconstruct_kap_text


def extract_dif_text(
    dif_el: etree._Element, rad_text: str | None, variant_rads: dict[str, str]
) -> str:
    """
    Extract text content from a dif element, replacing tld with rad.

    Args:
        dif_el: The lxml dif element (or ref/refgrp element)
        rad_text: The base rad text for tld replacement
        variant_rads: Dictionary mapping var attributes to variant rad texts

    Returns:
        The text content of the dif element with tld replaced
    """
    parts: list[str] = []

    def _collect_text(el: etree._Element) -> None:
        """Collect text from an element, handling tld, ref, and refgrp children."""
        if el.text:
            parts.append(el.text)

        for child in el:
            if child.tag == "tld":
                if rad_text is not None:
                    lit = child.get("lit", "")
                    var = child.get("var", "")
                    rad_to_use = variant_rads.get(var, rad_text) if var else rad_text
                    if lit:
                        parts.append(lit + rad_to_use[1:])
                    else:
                        parts.append(rad_to_use)
            elif child.tag in ("ref", "refgrp"):
                _collect_text(child)
            # Other tags (ekz, klr, etc.): skip element content

            # Always include tail text (text after the child element)
            if child.tail:
                parts.append(child.tail)

    _collect_text(dif_el)

    # Join all parts and normalize whitespace
    result = " ".join("".join(parts).split())

    # Ensure proper ending punctuation
    if result.endswith(":"):
        result = result[:-1] + "."
    elif result and result[-1] not in ".!?;":
        result = result + "."

    return result


def process_snc_list(
    snc_elements: list[etree._Element],
    rad_text: str | None,
    variant_rads: dict[str, str],
    base_num: str = "",
) -> dict[str, str]:
    """
    Process a list of snc/subsnc elements and extract their definitions.

    Args:
        snc_elements: List of lxml snc/subsnc elements
        rad_text: The base rad text for tld replacement
        variant_rads: Dictionary mapping var attributes to variant rad texts
        base_num: Base number for this level (empty for top level)

    Returns:
        Dictionary mapping sense numbers to definitions
    """
    result: dict[str, str] = {}
    snc_count = 0

    for snc_el in snc_elements:
        snc_count += 1
        sense_num = f"{base_num}.{snc_count}" if base_num else str(snc_count)

        # Look for definition: dif, ref[@tip="dif"], or refgrp[@tip="dif"]
        dif_el = snc_el.find("dif")
        if dif_el is None:
            dif_el = snc_el.find('ref[@tip="dif"]')
        if dif_el is None:
            dif_el = snc_el.find('refgrp[@tip="dif"]')

        if dif_el is not None:
            dif_text = extract_dif_text(dif_el, rad_text, variant_rads)
            if dif_text:
                result[sense_num] = dif_text

        # Process nested snc/subsnc direct children
        nested = [ch for ch in snc_el if ch.tag in ("snc", "subsnc")]
        if nested:
            sub_results = process_snc_list(nested, rad_text, variant_rads, sense_num)
            result.update(sub_results)

    return result


def process_drv_or_subdrv(
    drv_el: etree._Element, rad_text: str | None, variant_rads: dict[str, str]
) -> dict[str, str]:
    """
    Process a drv or subdrv element and extract sense definitions.

    Args:
        drv_el: The lxml drv or subdrv element
        rad_text: The base rad text for tld replacement
        variant_rads: Dictionary mapping var attributes to variant rad texts

    Returns:
        Dictionary mapping sense numbers to definitions
    """
    snc_elements = drv_el.findall("snc")
    return process_snc_list(snc_elements, rad_text, variant_rads)


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

        # Get base rad text from article-level kap
        rad_els = tree.xpath("//art/kap/rad")
        rad_text: str | None = rad_els[0].text if rad_els else None

        # Get variant rads (rad elements with var attribute anywhere in art/kap)
        variant_rads: dict[str, str] = {}
        for rad_el in tree.xpath("//art/kap//rad[@var]"):
            var = rad_el.get("var", "")
            if var and rad_el.text:
                variant_rads[var] = rad_el.text

        # Process all drv and subdrv elements
        for tag in ("drv", "subdrv"):
            for el in tree.xpath(f"//{tag}"):
                kap_el = el.find("kap")
                if kap_el is not None:
                    kap_texts = reconstruct_kap_text(kap_el, rad_text, variant_rads)
                    senses = process_drv_or_subdrv(el, rad_text, variant_rads)
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
        help="Output JSON file path (writes single merged JSON instead of zipfile)",
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

    if args.output:
        # -o mode: merge all senses into a single JSON file
        all_senses: dict[str, dict[str, str]] = {}
        for xml_file in tqdm(xml_files, desc="Processing XML files", unit="file"):
            file_senses = process_file(xml_file, xml_parser)
            all_senses.update(file_senses)

        output_path = pathlib.Path(args.output)
        with open(output_path, "w", encoding="UTF-8") as f:
            json.dump(all_senses, f, ensure_ascii=False, indent=2)
        print(f"\nExtracted senses for {len(all_senses)} kap entries")
        print(f"Results written to {output_path}")
    else:
        # Default mode: generate a zipfile with one JSON per XML file
        genfiles_path = get_genfiles_path()
        if genfiles_path is None:
            print(
                "Error: genfiles path not configured. "
                "Run 'python download_revo.py' to set it up.",
                file=sys.stderr,
            )
            sys.exit(1)
        genfiles_path.mkdir(parents=True, exist_ok=True)
        zip_path = genfiles_path / "senses.zip"

        total_entries = 0
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for xml_file in tqdm(xml_files, desc="Processing XML files", unit="file"):
                file_senses = process_file(xml_file, xml_parser)
                if file_senses:
                    json_bytes = json.dumps(
                        file_senses, ensure_ascii=False
                    ).encode("utf-8")
                    zf.writestr(
                        f"jsondata/{xml_file.stem}.json", json_bytes
                    )
                    total_entries += len(file_senses)

        print(f"\nExtracted senses for {total_entries} kap entries")
        print(f"Results written to {zip_path}")


if __name__ == "__main__":
    main()

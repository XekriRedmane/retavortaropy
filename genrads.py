"""
Command line tool to extract rad values from all XML files in a directory.
Creates a dictionary mapping rad text to XML file paths.
Includes both base rads and variant rads.
"""

import argparse
import json
import pathlib
import sys
from lxml import etree
from tqdm import tqdm

from config import get_revo_path, get_genfiles_path
from retavortaropy.xmlparse import DTDResolver


def process_file(xml_path: pathlib.Path, parser: etree.XMLParser) -> dict[str, str]:
    """Processes a single XML file and extracts all rad texts."""
    rad_to_file: dict[str, str] = {}

    try:
        with open(xml_path, "r", encoding="UTF-8") as f:
            tree = etree.parse(f, parser=parser)

        # Base rads (without var attribute)
        for rad_el in tree.xpath("//art/kap/rad[not(@var)]"):
            if rad_el.text:
                rad_to_file[rad_el.text] = xml_path.stem

        # Variant rads (inside var/kap elements)
        for rad_el in tree.xpath("//art/kap/var/kap/rad"):
            if rad_el.text:
                rad_to_file[rad_el.text] = xml_path.stem

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
        default=None,
        help="Directory containing XML files or single XML file",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output JSON file path",
    )
    args = parser.parse_args()

    if args.output is None:
        genfiles_path = get_genfiles_path()
        if genfiles_path is None:
            print(
                "Error: genfiles path not configured. "
                "Run 'python download_revo.py' to set it up.",
                file=sys.stderr,
            )
            sys.exit(1)
        genfiles_path.mkdir(parents=True, exist_ok=True)
        args.output = str(genfiles_path / "rad_dictionary.json")

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

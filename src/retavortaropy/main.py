"""Parses a retavortaro XML file."""

# pylint: disable=c-extension-no-member

from dataclasses import asdict
import json
import sys
from typing import cast
import pathlib

from lxml import etree
from lxml.sax import saxify  # pylint: disable=no-name-in-module
from tqdm import tqdm

from retavortaropy import utils
from retavortaropy.data import vortaro
from config import get_revo_path
from retavortaropy.xmlparse import DTDResolver, RevoContentHandler


def remove_trd(element: vortaro.Element) -> None:
    """Remove trd elements."""

    # Drill down into the element, and if it HasContent, then drill down
    # to each list element. If a list element is a Trd or a TrdGrp, then
    # remove it from the list.

    if not isinstance(element, vortaro.HasContent):
        return

    element = cast(vortaro.HasContent[vortaro.Element], element)
    content = element.content
    for i in range(len(content) - 1, -1, -1):
        if isinstance(content[i], (vortaro.Trd, vortaro.TrdGrp)):
            content.pop(i)
            continue
        remove_trd(content[i])


def main() -> None:
    """Main function."""
    parser = etree.XMLParser(load_dtd=True, resolve_entities=True)
    parser.resolvers.add(DTDResolver())

    files_and_kap: list[tuple[pathlib.Path, str]] = []

    revo_dir = get_revo_path()
    if revo_dir is None:
        print(
            "Error: revo-fonto dictionary not found. "
            "Run 'python download_revo.py' to download it.",
            file=sys.stderr,
        )
        sys.exit(1)
    for xml_file in tqdm(list(revo_dir.glob("*.xml"))):
        # print(f"Processing {xml_file.name}")
        try:
            with open(xml_file, "r", encoding="UTF-8") as f:
                tree = etree.parse(f, parser=parser)
            handler = RevoContentHandler()
            saxify(tree, handler)
            # root = tree.getroot()
            # print(etree.tostring(root, pretty_print=True, encoding="unicode"))

            root = handler.root
            # remove_trd(root)
            # print(root)
            root_dict = asdict(root)
            root_dict = root.json_encode()
            root_json = json.dumps(root_dict, ensure_ascii=False, indent=2)
            # print(root_json)

            rad = utils.get_closest_rad_text(root)
            uzos = utils.find_uzos_with_kaps(root)
            geog_uzos = utils.filter_uzos_by_fak(uzos, "GEOG")
            if not geog_uzos:
                continue
            for _, kap in geog_uzos:
                files_and_kap.append((xml_file, utils.get_text_content(kap, rad)))
        except Exception as e:
            print(f"Error processing {xml_file.name}: {e}")

    with open("geog_uzos.json", "w", encoding="UTF-8") as f:
        json.dump(files_and_kap, f, ensure_ascii=False, indent=2)
    print(f"Found {len(files_and_kap)} geog uzos")


if __name__ == "__main__":
    main()

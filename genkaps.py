"""
Command line tool to extract drv kap values from all XML files in a directory.
Creates a dictionary mapping kap text to XML file paths.
Handles variants by expanding them into separate kap entries.
"""
import argparse
import json
import pathlib
import re
from typing import Any
from lxml import etree
from lxml.sax import saxify
from jsonpath_ng import parse
from tqdm import tqdm

from retavortaropy.main import DTDResolver, RevoContentHandler
from retavortaropy import utils


def get_variant_rads(root_dict: dict[str, Any]) -> dict[str, str]:
    """
    Extract variant rad texts from the root art/kap element.
    Returns a dict mapping var attribute values to rad text.
    """
    variant_rads: dict[str, str] = {}
    
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
                        if var and text:
                            variant_rads[var] = text
                    elif "var" in kap_item:
                        var_data = kap_item["var"]
                        if "kap" in var_data:
                            var_kap_wrapper = var_data["kap"]
                            if "kap" in var_kap_wrapper:
                                var_kap = var_kap_wrapper["kap"]
                                var_content = var_kap.get("content", [])
                                for var_item in var_content:
                                    if "rad" in var_item:
                                        rad_data = var_item["rad"]
                                        var_attr = rad_data.get("var", "")
                                        text = rad_data.get("text", "")
                                        if var_attr and text:
                                            variant_rads[var_attr] = text
    except Exception:
        pass
    
    return variant_rads


def get_json_kap_text(kap_dict: dict[str, Any], rad_text: str | None,
                      variant_rads: dict[str, str] | None = None, include_vars: bool = True) -> list[str]:
    """
    Reconstructs kap text(s) from JSON, processing tld and variants.
    Returns list of kap texts (base kap + any variants).
    """
    if not kap_dict:
        return []

    content = kap_dict.get("content", [])
    if not content:
        return []

    if variant_rads is None:
        variant_rads = {}

    base_parts: list[str] = []
    variants: list[str] = []

    for item in content:
        if "text" in item:
            text = item["text"]
            if text.strip():
                base_parts.append(text)
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
                    base_parts.append(lit + rad_to_use[1:])
                else:
                    base_parts.append(rad_to_use)
        elif "rad" in item:
            rad_data = item["rad"]
            if "text" in rad_data:
                base_parts.append(rad_data["text"])
        elif "var" in item and include_vars:
            var_data = item["var"]
            if "kap" in var_data:
                var_kap_wrapper = var_data["kap"]
                if "kap" in var_kap_wrapper:
                    var_kap_inner = var_kap_wrapper["kap"]
                    var_texts = get_json_kap_text(var_kap_inner, rad_text, variant_rads, include_vars=False)
                    variants.extend(var_texts)

    base_text: str = "".join(base_parts).strip()
    base_text = re.sub(r'[,;]\s*$', '', base_text).strip()

    result: list[str] = []
    if base_text:
        result.append(base_text)
    result.extend(variants)

    return result


def process_file(xml_path: pathlib.Path, parser: etree.XMLParser) -> dict[str, str]:
    """Processes a single XML file and returns kap->file mapping."""
    kap_to_file: dict[str, str] = {}

    try:
        with open(xml_path, "r", encoding="UTF-8") as f:
            tree = etree.parse(f, parser=parser)

        handler = RevoContentHandler()
        saxify(tree, handler)
        root = handler.root
        root_dict: dict[str, Any] = root.json_encode()

        rad_text: str | None = utils.json_get_closest_rad_text(root_dict)
        variant_rads: dict[str, str] = get_variant_rads(root_dict)

        jsonpath_expression = parse('$..drv')
        matches = jsonpath_expression.find(root_dict)

        for match in matches:
            drv_data = match.value
            kap_wrapper = drv_data.get('kap')
            if kap_wrapper and 'kap' in kap_wrapper:
                kap_inner = kap_wrapper['kap']
                kap_texts = get_json_kap_text(kap_inner, rad_text, variant_rads)
                for kap_text in kap_texts:
                    if kap_text:
                        kap_to_file[kap_text] = str(xml_path)

    except Exception as e:
        print(f"Error processing {xml_path.name}: {e}")

    return kap_to_file


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract drv kap values from Revo XML files."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="f:/revo-fonto/revo",
        help="Directory or file"
    )
    parser.add_argument(
        "-o", "--output",
        default="kap_dictionary.json",
        help="Output JSON file"
    )
    args = parser.parse_args()

    input_path = pathlib.Path(args.path)
    if not input_path.exists():
        print(f"Error: Path {input_path} not found.")
        return

    if input_path.is_file():
        xml_files = [input_path]
    elif input_path.is_dir():
        xml_files = list(input_path.glob("*.xml"))
    else:
        print(f"Error: {input_path} is neither file nor directory.")
        return

    if not xml_files:
        print(f"No XML files found in {input_path}")
        return

    xml_parser = etree.XMLParser(load_dtd=True, resolve_entities=True)
    xml_parser.resolvers.add(DTDResolver())

    all_kaps: dict[str, str] = {}

    for xml_file in tqdm(xml_files, desc="Processing XML files", unit="file"):
        file_kaps: dict[str, str] = process_file(xml_file, xml_parser)
        all_kaps.update(file_kaps)

    output_path = pathlib.Path(args.output)
    with open(output_path, "w", encoding="UTF-8") as f:
        json.dump(all_kaps, f, ensure_ascii=False, indent=2)

    print(f"\nExtracted {len(all_kaps)} unique kap entries")
    print(f"Results written to {output_path}")


if __name__ == "__main__":
    main()

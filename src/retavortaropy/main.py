"""Parses a retavortaro XML file."""

# pylint: disable=c-extension-no-member

from dataclasses import asdict
from importlib.resources import files
import inspect
import json
from typing import cast, Any
from xml.sax.handler import ContentHandler
from xml.sax.xmlreader import AttributesNSImpl

from lxml import etree
from lxml.sax import saxify  # pylint: disable=no-name-in-module
import pathlib
from tqdm import tqdm

from retavortaropy import utils
from retavortaropy.data import vortaro


class DTDResolver(etree.Resolver):
    """Resolver for DTDs."""
    def resolve(
        self, system_url: str | None, public_id: str | None, context: Any
    ) -> Any:
        """Resolve a DTD."""
        if system_url is None:
            return None
        del public_id  # Unused
        # print(f"Resolving url {system_url}")
        if system_url.startswith("file:/"):
            resource_path = system_url[6:]
        elif system_url.startswith("../"):
            system_url = system_url.replace("../", "")
            resource_path = str(files("retavortaropy").joinpath(system_url))
        else:
            raise ValueError(f"Unsupported url {system_url}")
        # print(f"Resolved to {resource_path}")
        return self.resolve_filename(str(resource_path), context)


class RevoContentHandler(ContentHandler):
    """Builds the tree."""

    root: vortaro.Element
    stack: list[vortaro.Element]

    def __init__(self):
        super().__init__()
        self.stack = []

    def startElementNS(
        self, name: tuple[str | None, str], qname: str | None, attrs: AttributesNSImpl
    ) -> None:
        parent = self.stack[-1] if len(self.stack) > 0 else None
        if qname not in vortaro.ELEMENT_TYPES:
            raise ValueError(f"Unimplemented element {qname}, parent {type(parent)}")
        element = vortaro.element_for(qname)
        self.stack.append(element)

        attributes = [
            name
            for name, value in inspect.getmembers(element)
            if not inspect.ismethod(value) and not name.startswith("__")
        ]
        for attr in attributes:
            if attr in ("text", "content", "kap"):
                continue
            if attr in attrs.getQNames():
                setattr(element, attr, attrs.getValueByQName(attr))

        if parent is None:
            return
        if isinstance(parent, vortaro.HasKap) and isinstance(element, vortaro.Kap):
            parent.kap = element
            return
        if isinstance(parent, vortaro.HasContent):
            parent = cast(vortaro.HasContent[vortaro.Element], parent)
            parent.append(element)

    def endElementNS(self, name: tuple[str | None, str], qname: str | None) -> None:
        parent = self.stack[-1] if len(self.stack) > 0 else None
        if qname in vortaro.ELEMENT_TYPES and isinstance(
            parent, vortaro.ELEMENT_TYPES[qname]
        ):
            self.root = self.stack.pop()
            return
        raise ValueError(f"End element {qname} not at top of stack ({type(parent)}")

    def characters(self, content: str):
        parent = self.stack[-1] if len(self.stack) > 0 else None

        if isinstance(parent, vortaro.TextOnlyElement):
            parent.text += content
            return

        if isinstance(parent, vortaro.HasTextInContent):
            parent = cast(vortaro.HasContent[vortaro.Element], parent)
            parent.append(vortaro.TextOnlyElement(text=content))
            return

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

    revo_dir = pathlib.Path("F:/revo-fonto/revo")
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

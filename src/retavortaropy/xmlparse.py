"""XML parsing utilities for retavortaro files."""

# pylint: disable=c-extension-no-member

from importlib.resources import files
from typing import Any, cast
from xml.sax.handler import ContentHandler
from xml.sax.xmlreader import AttributesNSImpl
import inspect

from lxml import etree

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
        if system_url.startswith("file:/"):
            resource_path = system_url[6:]
        elif system_url.startswith("../"):
            system_url = system_url.replace("../", "")
            resource_path = str(files("retavortaropy").joinpath(system_url))
        else:
            raise ValueError(f"Unsupported url {system_url}")
        return self.resolve_filename(str(resource_path), context)


class RevoContentHandler(ContentHandler):
    """Builds the tree."""

    root: vortaro.Element
    stack: list[vortaro.Element]

    def __init__(self) -> None:
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

    def characters(self, content: str) -> None:
        parent = self.stack[-1] if len(self.stack) > 0 else None

        if isinstance(parent, vortaro.TextOnlyElement):
            parent.text += content
            return

        if isinstance(parent, vortaro.HasTextInContent):
            parent = cast(vortaro.HasContent[vortaro.Element], parent)
            parent.append(vortaro.TextOnlyElement(text=content))
            return

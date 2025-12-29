"""Utility functions for processing vortaro elements."""

from typing import Any
from retavortaropy.data import vortaro

def find_uzos_with_kaps(element: vortaro.Element) -> list[tuple[vortaro.Uzo, vortaro.Kap | None]]:
    """
    Finds all Uzo elements at any depth and returns them with their nearest ancestor Kap.

    Args:
        element: The root element to start searching from.

    Returns:
        A list of tuples, each containing a Uzo element and its nearest Kap ancestor (or None).
    """
    results: list[tuple[vortaro.Uzo, vortaro.Kap | None]] = []

    # Helper function for recursion
    def _traverse(current_element: vortaro.Element, current_kap: vortaro.Kap | None):
        # Update current_kap if this element has one
        if isinstance(current_element, vortaro.HasKap) and current_element.kap is not None:
            current_kap = current_element.kap

        # If this is a Uzo element, record it
        if isinstance(current_element, vortaro.Uzo):
            results.append((current_element, current_kap))

        # Recurse into content if applicable
        if isinstance(current_element, vortaro.HasContent):
            for child in current_element.content:
                if isinstance(child, vortaro.Element):
                    _traverse(child, current_kap)

    _traverse(element, None)
    return results


def get_text_content(element: vortaro.HasTextInContent, rad: str | None = None) -> str:
    """
    Gets the text content of a HasTextInContent element, non-recursively.

    Args:
        element: The element to extract text from.
        rad: Optional replacement string for Tld elements.

    Returns:
        Concatenated text of TextOnlyElement children, with Tld replacement if specified.
    """
    parts = []
    for child in element.content:
        if isinstance(child, vortaro.TextOnlyElement):
            parts.append(child.text)
        elif isinstance(child, vortaro.Tld) and rad is not None:
            if child.lit:
                parts.append(child.lit + rad[1:])
            else:
                parts.append(rad)

    return "".join(parts)


def filter_uzos_by_fak(
    uzos_with_kaps: list[tuple[vortaro.Uzo, vortaro.Kap | None]],
    fak: str
) -> list[tuple[vortaro.Uzo, vortaro.Kap | None]]:
    """
    Filters Uzo elements by tip="fak" and exact text content matches.

    Args:
        uzos_with_kaps: The list of (Uzo, Kap) tuples to filter.
        fak: The text content to match (e.g. "MAT").

    Returns:
        Filtered list of tuples.
    """
    filtered = []
    for uzo, kap in uzos_with_kaps:
        if uzo.tip == "fak":
            text = get_text_content(uzo).strip()
            if text == fak:
                filtered.append((uzo, kap))
    return filtered


def get_closest_rad_text(vortaro_element: vortaro.Vortaro) -> str | None:
    """
    Extracts the text of the first Rad element found in the Vortaro's Article's Kap.

    Args:
        vortaro_element: The Vortaro element to search.

    Returns:
        The text of the Rad element, or None if not found.
    """
    for child in vortaro_element.content:
        if isinstance(child, vortaro.Art):
            if child.kap is None:
                continue
            for kap_child in child.kap.content:
                if isinstance(kap_child, vortaro.Rad):
                    return kap_child.text
    return None


def json_get_closest_rad_text(root_dict: dict[str, Any]) -> str | None:
    """
    Extracts the text of the first Rad element found in the Vortaro's Article's Kap (JSON version).

    Args:
        root_dict: The JSON dict of the Vortaro element.

    Returns:
        The text of the Rad element, or None if not found.
    """
    if "vortaro" not in root_dict:
        return None

    vortaro_content = root_dict["vortaro"].get("content", [])
    for item in vortaro_content:
        if "art" in item:
            art = item["art"]
            # Art has "kap" field directly if it exists (via HasKap logic in json_encode)
            if "kap" in art:
                kap_wrapper = art["kap"]
                if "kap" in kap_wrapper:
                    kap = kap_wrapper["kap"]
                    # Kap has "content"
                    kap_content = kap.get("content", [])
                    for kap_item in kap_content:
                        if "rad" in kap_item:
                            return kap_item["rad"].get("text", "")
    return None

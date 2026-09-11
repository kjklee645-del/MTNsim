from __future__ import annotations

from pathlib import Path

try:
    from defusedxml import ElementTree as ET
    from defusedxml.common import DefusedXmlException
except ImportError:  # pragma: no cover - exercised only when dependency is unavailable
    import xml.etree.ElementTree as ET

    class DefusedXmlException(ValueError):
        """Fallback exception when defusedxml is unavailable."""

from mtnsim.security.exceptions import ConfigValidationError


def parse_xml(path: str | Path, *, label: str) -> ET.ElementTree:
    xml_path = Path(path).expanduser().resolve()
    try:
        _reject_unsafe_xml(xml_path)
        return ET.parse(xml_path)
    except (ET.ParseError, DefusedXmlException) as exc:
        raise ConfigValidationError(f"{label} could not be parsed safely: {xml_path}") from exc
    except OSError as exc:
        raise ConfigValidationError(f"{label} could not be read: {xml_path}") from exc


def parse_xml_root(path: str | Path, *, label: str) -> ET.Element:
    return parse_xml(path, label=label).getroot()


def _reject_unsafe_xml(path: Path) -> None:
    content = path.read_bytes().upper()
    if b"<!DOCTYPE" in content or b"<!ENTITY" in content:
        raise DefusedXmlException(f"Unsafe XML declarations are not allowed: {path}")

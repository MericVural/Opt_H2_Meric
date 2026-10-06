"""Unambiguous numeric GUI inputs and atomic job records; no model equations."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import os
from pathlib import Path
import re


def sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_json(path: str | Path, value: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def numeric_value(text) -> float:
    if isinstance(text, bool):
        raise ValueError("Boolesche Werte sind keine Zahlen.")
    try:
        value = float(str(text).strip().replace(",", "."))
    except (ValueError, TypeError) as exc:
        raise ValueError("Eine endliche Zahl mit Dezimalpunkt oder Dezimalkomma eingeben.") from exc
    if not math.isfinite(value):
        raise ValueError("Der Wert muss endlich sein.")
    return value


def parse_wacc_percent(text) -> float:
    """The UI field is explicitly in percent: '3,30 %' -> 0.033."""
    value = numeric_value(str(text).strip().removesuffix("%").strip()) / 100.0
    if not 0 <= value < 1:
        raise ValueError("WACC in Prozent muss zwischen 0 und unter 100 liegen.")
    return value


def parse_values(explicit_text: str = "", min_value=None, max_value=None, step=None,
                 *, percent: bool = False, max_values: int = 1000) -> list[float]:
    """Explicit values use semicolons/newlines/spaces; comma is a decimal mark.

    Decimal arithmetic avoids floating-step drift. A non-aligned upper bound
    is not added: every generated point must lie on the user's step grid.
    """
    if explicit_text.strip():
        if any(value not in (None, "") for value in (min_value, max_value, step)):
            raise ValueError("Explizite Werte oder Bereich wählen, nicht beide zugleich.")
        parts = [part for part in re.split(r"[;\s]+", explicit_text.strip()) if part]
        values = [numeric_value(part.removesuffix("%")) for part in parts if part != "%"]
    else:
        if any(value in (None, "") for value in (min_value, max_value, step)):
            raise ValueError("Minimum, Maximum und Schrittweite sind erforderlich.")
        try:
            lower, upper, increment = (Decimal(str(value).replace(",", "."))
                                       for value in (min_value, max_value, step))
        except InvalidOperation as exc:
            raise ValueError("Ungültiger Zahlenbereich.") from exc
        if not all(value.is_finite() for value in (lower, upper, increment)) or increment <= 0 or upper < lower:
            raise ValueError("Bereich verlangt Maximum ≥ Minimum und eine positive Schrittweite.")
        count = int((upper - lower) // increment) + 1
        if count > max_values:
            raise ValueError(f"Höchstens {max_values} Sensitivitätswerte pro Parameter.")
        values = [float(lower + increment * index) for index in range(count)]
    if not values or not all(math.isfinite(value) for value in values) or len(values) > max_values or len(set(values)) != len(values):
        raise ValueError("Werte müssen eindeutig sein; die maximale Anzahl darf nicht überschritten werden.")
    return [value / 100 if percent else value for value in values]


def read_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))

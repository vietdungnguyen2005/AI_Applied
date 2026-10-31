import csv
import io
from dataclasses import dataclass
from typing import Literal

Encoding = Literal["UTF-8", "CP932"]


@dataclass(frozen=True)
class CSVQuality:
    code: str
    headers: tuple[str, ...] = ()
    rows: int = 0


def inspect_csv(raw: bytes, encoding: Encoding) -> CSVQuality:
    """Offline structure QA only; does not emulate Java business validation."""
    if not raw or len(raw) > 5_000_000:
        return CSVQuality("byte_limit")
    try:
        decoded = raw.decode(encoding, errors="strict")
    except UnicodeError:
        return CSVQuality("decode_error")
    try:
        reader = csv.reader(io.StringIO(decoded, newline=""), strict=True)
        headers = tuple(h.strip() for h in next(reader))
        if not headers or any(not h for h in headers):
            return CSVQuality("missing_header")
        if len(set(headers)) != len(headers):
            return CSVQuality("duplicate_header", headers)
        rows = 0
        for row in reader:
            rows += 1
            if rows > 1000:
                return CSVQuality("row_limit", headers, rows)
            if len(row) != len(headers):
                return CSVQuality("width_mismatch", headers, rows)
        return CSVQuality("ok" if rows else "no_rows", headers, rows)
    except (StopIteration, csv.Error):
        return CSVQuality("malformed_csv")


@dataclass(frozen=True)
class TextQuality:
    status: str
    extraction_method: str
    extraction_confidence: None = None
    ocr_performed: bool = False


def inspect_text(raw: bytes, media_type: str) -> TextQuality:
    """Strict text-only fixture gate, never a PDF/DOCX/OCR parser."""
    if media_type not in {"text/plain", "text/markdown"}:
        return TextQuality("unsupported", "none")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError:
        return TextQuality("invalid_utf8", "strict_utf8")
    return TextQuality("verified_text" if text.strip() else "empty", "strict_utf8")

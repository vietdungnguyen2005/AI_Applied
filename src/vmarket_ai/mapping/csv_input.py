import csv
import io
import unicodedata
from dataclasses import dataclass

from vmarket_ai.datasets.quality import Encoding
from vmarket_ai.mapping.spec import MappingError


@dataclass(frozen=True)
class ParsedCSV:
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]

    def sample(self) -> tuple[list[list[str]], bool]:
        return [[s[:160] for s in r] for r in self.rows[:2]], any(
            len(s) > 160 for r in self.rows[:2] for s in r
        )


def parse_original(raw: bytes, encoding: Encoding) -> ParsedCSV:
    if not raw or len(raw) > 5_000_000:
        raise MappingError("INPUT_TOO_LARGE", 413)
    try:
        text = raw.decode(encoding, errors="strict")
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        headers = tuple(next(reader))
        # Reject rather than silently trim/normalize or strip a BOM from authoritative names.
        if not 1 <= len(headers) <= 100 or any(
            not h
            or h != h.strip()
            or len(h.encode("utf-16-le")) // 2 > 80
            or any(ord(c) < 32 or 127 <= ord(c) <= 159 or c == "\ufeff" for c in h)
            for h in headers
        ):
            raise MappingError("HEADER_INVALID", 400)
        identities = [unicodedata.normalize("NFKC", h).casefold() for h in headers]
        if len(set(identities)) != len(headers):
            raise MappingError("HEADER_AMBIGUOUS", 400)
        rows: list[tuple[str, ...]] = []
        for row in reader:
            if len(rows) >= 1000 or len(row) != len(headers):
                raise MappingError("CSV_STRUCTURE_INVALID", 400)
            rows.append(tuple(row))
        if not rows:
            raise MappingError("CSV_STRUCTURE_INVALID", 400)
        return ParsedCSV(headers, tuple(rows))
    except (UnicodeError, csv.Error, StopIteration):
        raise MappingError("CSV_STRUCTURE_INVALID", 400) from None

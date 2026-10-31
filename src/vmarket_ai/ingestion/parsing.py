"""Strict extraction in a bounded child process. No OCR, URLs or external relationships."""

import base64
import io
import json
import os
import re
import subprocess
import sys
import unicodedata
import zipfile
from collections import Counter

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader
from pypdf.generic import DictionaryObject

from vmarket_ai.ingestion.spec import (
    PARSER_VERSION,
    ChunkConfig,
    Extraction,
    IngestionError,
    Part,
    Section,
)

MAX_BYTES = 5_000_000
MAX_CHARS = 1_000_000
MEDIA = {
    "text/plain",
    "text/markdown",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
    if any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise IngestionError("invalid_text")
    return "\n".join(line.rstrip() for line in value.split("\n")).strip()


def extract_in_worker(raw: bytes, media_type: str) -> Extraction:
    """Internal worker entry; callers use extract() with enforced wall-clock timeout."""
    if not 0 < len(raw) <= MAX_BYTES or media_type not in MEDIA:
        raise IngestionError("size_or_media")
    sections: list[Section] = []
    total = 0

    def add(locator: str, value: str) -> None:
        nonlocal total
        total += len(value)
        if total > MAX_CHARS:
            raise IngestionError("text_limit")
        cleaned = normalize(value)
        if cleaned:
            if len(sections) >= 5000:
                raise IngestionError("text_limit")
            sections.append(Section(locator=locator, text=cleaned))

    if media_type in {"text/plain", "text/markdown"}:
        try:
            value = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise IngestionError("invalid_encoding") from None
        if value.startswith("\ufeff") or value.startswith(("%PDF", "PK\x03\x04")):
            raise IngestionError("media_mismatch")
        counts: Counter[str] = Counter()
        locator = "section:intro"
        lines: list[str] = []
        for line in value.splitlines():
            heading = re.fullmatch(r"#{1,6}\s+(.+)", line)
            if heading:
                add(locator, "\n".join(lines))
                title = heading.group(1).strip()
                counts[title] += 1
                suffix = f":{counts[title]}" if counts[title] > 1 else ""
                locator, lines = f"section:{title}{suffix}", []
            else:
                lines.append(line)
        add(locator, "\n".join(lines))
        parser = "strict-utf8-headings"
    elif media_type == "application/pdf":
        if not raw.startswith(b"%PDF-"):
            raise IngestionError("media_mismatch")
        reader = PdfReader(io.BytesIO(raw), strict=True)
        if reader.is_encrypted:
            raise IngestionError("encrypted_pdf")
        if not 0 < len(reader.pages) <= 200:
            raise IngestionError("page_limit")
        root = reader.trailer["/Root"]
        if not isinstance(root, DictionaryObject):
            raise IngestionError("parse_failed")
        if any(k in root for k in ("/OpenAction", "/AA", "/AcroForm")):
            raise IngestionError("active_pdf")
        names = root.get("/Names")
        if names and any(k in names.get_object() for k in ("/JavaScript", "/EmbeddedFiles")):
            raise IngestionError("active_pdf")
        for i, page in enumerate(reader.pages, 1):
            if "/AA" in page:
                raise IngestionError("active_pdf")
            value = page.extract_text()
            if not value or not value.strip():
                raise IngestionError("unextractable_page_no_ocr")
            add(f"page:{i}", value)
        parser = "pypdf-text-pages"
    else:
        from defusedxml.ElementTree import fromstring  # type: ignore[import-untyped]

        if not zipfile.is_zipfile(io.BytesIO(raw)):
            raise IngestionError("media_mismatch")
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            names = [e.filename for e in entries]
            if (
                len(entries) > 1000
                or len(names) != len(set(names))
                or sum(e.file_size for e in entries) > 20_000_000
                or any(e.file_size > 10_000_000 or e.flag_bits & 1 for e in entries)
            ):
                raise IngestionError("docx_expansion_limit")
            if "word/document.xml" not in names or "[Content_Types].xml" not in names:
                raise IngestionError("invalid_docx")
            for entry in entries:
                if "vba" in entry.filename.lower() or entry.filename.startswith("word/embeddings/"):
                    raise IngestionError("active_docx")
                if re.fullmatch(
                    r"word/(header\d+|footer\d+|footnotes|endnotes)\.xml", entry.filename
                ):
                    raise IngestionError("unsupported_docx_structure")
                if entry.filename.endswith((".xml", ".rels")):
                    content = archive.read(entry)
                    element = fromstring(content)  # DTD/entity expansion rejected.
                    if entry.filename == "word/document.xml":
                        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
                        unsupported = {
                            ns + name
                            for name in (
                                "drawing",
                                "pict",
                                "object",
                                "altChunk",
                                "sdt",
                                "ins",
                                "del",
                                "hyperlink",
                                "instrText",
                                "txbxContent",
                            )
                        }
                        if any(e.tag in unsupported for e in element.iter()) or any(
                            len(list(table.iter(ns + "tbl"))) > 1
                            for table in element.iter(ns + "tbl")
                        ):
                            raise IngestionError("unsupported_docx_structure")
                    if entry.filename.endswith(".rels") and any(
                        r.attrib.get("TargetMode", "").lower() == "external" for r in element
                    ):
                        raise IngestionError("external_docx_relationship")
        doc = Document(io.BytesIO(raw))
        for i, block in enumerate(doc.iter_inner_content(), 1):
            if isinstance(block, Paragraph):
                add(f"paragraph:{i}", block.text)
            elif isinstance(block, Table):
                for r, row in enumerate(block.rows, 1):
                    for c, cell in enumerate(row.cells, 1):
                        add(f"table:{i}:row:{r}:cell:{c}", cell.text)
        parser = "python-docx-body-tables"
    if not sections:
        raise IngestionError("empty_document")
    return Extraction(sections=tuple(sections), parser=f"{PARSER_VERSION}/{parser}")


def extract(raw: bytes, media_type: str, *, timeout: float = 10) -> Extraction:
    if not 0 < len(raw) <= MAX_BYTES or media_type not in MEDIA or not 0 < timeout <= 10:
        raise IngestionError("size_or_media")
    payload = json.dumps({"raw": base64.b64encode(raw).decode(), "media_type": media_type})
    env = {
        k: v
        for k, v in os.environ.items()
        if k.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LANG", "SYSTEMDRIVE"}
    }
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "vmarket_ai.ingestion.worker"],
            input=payload.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            env=env,
            check=False,
        )
        if result.returncode:
            # Only static allowlisted error codes cross the process boundary.
            code = result.stdout.decode("ascii", errors="ignore").strip()
            allowed = {
                "invalid_encoding",
                "media_mismatch",
                "empty_document",
                "text_limit",
                "encrypted_pdf",
                "page_limit",
                "active_pdf",
                "unextractable_page_no_ocr",
                "docx_expansion_limit",
                "invalid_docx",
                "active_docx",
                "external_docx_relationship",
                "unsupported_docx_structure",
                "invalid_text",
                "parse_failed",
            }
            raise IngestionError(code if code in allowed else "parse_failed")
        return Extraction.model_validate_json(result.stdout)
    except subprocess.TimeoutExpired:
        raise IngestionError("parse_timeout") from None
    except (OSError, ValueError):
        raise IngestionError("parse_failed") from None


def chunk(extraction: Extraction, config: ChunkConfig) -> tuple[Part, ...]:
    import hashlib

    parts: list[Part] = []
    for section in extraction.sections:
        for start in range(0, len(section.text), config.size - config.overlap):
            if len(parts) >= 5000:
                raise IngestionError("chunk_limit")
            end = min(start + config.size, len(section.text))
            value = section.text[start:end]
            parts.append(
                Part(
                    ordinal=len(parts),
                    locator=section.locator,
                    start=start,
                    end=end,
                    text=value,
                    text_sha256=hashlib.sha256(value.encode()).hexdigest(),
                )
            )
            if end == len(section.text):
                break
    if len(parts) > 5000:
        raise IngestionError("chunk_limit")
    return tuple(parts)

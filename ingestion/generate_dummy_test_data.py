from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_DIR = ROOT / "documents"


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_page_stream(lines: list[str]) -> bytes:
    escaped_lines = [_escape_pdf_text(line) for line in lines]
    parts = ["BT", "/F1 12 Tf", "72 740 Td"]
    if escaped_lines:
        parts.append(f"({escaped_lines[0]}) Tj")
        for line in escaped_lines[1:]:
            parts.append("0 -18 Td")
            parts.append(f"({line}) Tj")
    parts.append("ET")
    return "\n".join(parts).encode("utf-8")


def _write_pdf(path: Path, lines: list[str]) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)  # pylint: disable=protected-access

    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref}),
        }
    )

    stream = DecodedStreamObject()
    stream.set_data(_build_page_stream(lines))
    stream_ref = writer._add_object(stream)  # pylint: disable=protected-access
    page[NameObject("/Contents")] = stream_ref

    with path.open("wb") as file_obj:
        writer.write(file_obj)


def _write_sidecar(path: Path, allowed_roles: list[str]) -> None:
    payload = {"allowed_roles": allowed_roles}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

    salary_lines = [
        "Salary Policy (Confidential)",
        "Only HR managers and admins may access salary records.",
        "Band S3 range: 95000 to 120000 USD.",
        "Bonus eligibility requires manager approval.",
    ]
    intern_lines = [
        "Intern Handbook",
        "Interns work on onboarding tasks and non-sensitive projects.",
        "Mentor check-ins happen every Friday.",
        "Use approved systems and never store credentials in code.",
    ]
    admin_lines = [
        "Admin Incident Runbook",
        "Escalate critical incidents within 15 minutes.",
        "Admin-only credentials are rotated every 30 days.",
        "Use break-glass access only during P1 events.",
    ]

    _write_pdf(DOCUMENTS_DIR / "salary-policy.pdf", salary_lines)
    _write_sidecar(DOCUMENTS_DIR / "salary-policy.json", ["HR_Manager", "Admin"])

    _write_pdf(DOCUMENTS_DIR / "intern-handbook.pdf", intern_lines)
    _write_sidecar(DOCUMENTS_DIR / "intern-handbook.json", ["Intern", "HR_Manager", "Admin"])

    _write_pdf(DOCUMENTS_DIR / "admin-runbook.pdf", admin_lines)
    _write_sidecar(DOCUMENTS_DIR / "admin-runbook.json", ["Admin"])

    print(f"Dummy test PDFs generated in {DOCUMENTS_DIR}")


if __name__ == "__main__":
    main()

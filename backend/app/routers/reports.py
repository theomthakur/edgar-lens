from __future__ import annotations

from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.db_models import ReportORM

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _plain(text: object) -> str:
    """Keep the built-in PDF fonts reliable for filing text from many sources."""
    return str(text).encode("ascii", "replace").decode("ascii")


def _lines(text: str, width: float, font: str, size: float) -> list[str]:
    words = _plain(text).split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and stringWidth(candidate, font, size) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def _draw_wrapped(canvas: Canvas, text: str, x: float, y: float, width: float, font: str, size: float, leading: float) -> float:
    canvas.setFont(font, size)
    for line in _lines(text, width, font, size):
        canvas.drawString(x, y, line)
        y -= leading
    return y


def _new_page(canvas: Canvas, page: int) -> float:
    canvas.showPage()
    canvas.setFillColor(HexColor("#17243A"))
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(54, 750, "EDGAR LENS / RESEARCH BRIEF")
    canvas.setStrokeColor(HexColor("#D6D0C4"))
    canvas.line(54, 740, 558, 740)
    canvas.setFillColor(HexColor("#657080"))
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(558, 750, f"PAGE {page}")
    return 714


@router.get("/{report_id}")
def get_report(report_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    report = db.get(ReportORM, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "reportId": report.report_id,
        "ticker": report.ticker,
        "summary": report.summary,
        "keyFindings": report.key_findings,
        "citations": [
            {
                "sourceTitle": c.source_title,
                "section": c.section,
                "excerpt": c.excerpt,
            }
            for c in report.citations
        ],
    }


@router.get("/{report_id}/pdf")
def download_report_pdf(report_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    """Create a portable, source-forward brief from the persisted report only."""
    report = db.get(ReportORM, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    stream = BytesIO()
    canvas = Canvas(stream, pagesize=letter, pageCompression=1)
    canvas.setTitle(f"EDGAR Lens - {report.ticker} research brief")
    canvas.setAuthor("EDGAR Lens")
    canvas.setFillColor(HexColor("#17243A"))
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(54, 750, "EDGAR LENS / RESEARCH BRIEF")
    canvas.setStrokeColor(HexColor("#D6D0C4"))
    canvas.line(54, 740, 558, 740)
    canvas.setFillColor(HexColor("#657080"))
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(558, 750, "SOURCE-BACKED NOTE")

    y = 694
    canvas.setFillColor(HexColor("#355F9E"))
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(54, y, "PUBLIC FILING RESEARCH")
    y -= 34
    canvas.setFillColor(HexColor("#17243A"))
    canvas.setFont("Helvetica-Bold", 30)
    canvas.drawString(54, y, f"{_plain(report.ticker)} research brief")
    y -= 40
    canvas.setFillColor(HexColor("#657080"))
    y = _draw_wrapped(canvas, report.summary, 54, y, 504, "Helvetica", 10.5, 16)
    y -= 16

    canvas.setStrokeColor(HexColor("#A64B3C"))
    canvas.setLineWidth(2)
    canvas.line(54, y, 105, y)
    y -= 22
    canvas.setFillColor(HexColor("#17243A"))
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(54, y, "KEY FINDINGS")
    y -= 22
    for index, finding in enumerate(report.key_findings, start=1):
        needed = max(1, len(_lines(str(finding), 462, "Helvetica", 10))) * 15 + 16
        if y - needed < 72:
            y = _new_page(canvas, 2)
        canvas.setFillColor(HexColor("#A64B3C"))
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(54, y, f"{index:02d}")
        canvas.setFillColor(HexColor("#17243A"))
        y = _draw_wrapped(canvas, str(finding), 96, y, 462, "Helvetica", 10, 15)
        y -= 8

    if y < 190:
        y = _new_page(canvas, 2)
    y -= 8
    canvas.setStrokeColor(HexColor("#C79D43"))
    canvas.setLineWidth(2)
    canvas.line(54, y, 105, y)
    y -= 22
    canvas.setFillColor(HexColor("#17243A"))
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(54, y, "SOURCE TRAIL")
    y -= 22

    page = 2
    for index, citation in enumerate(report.citations, start=1):
        citation_lines = _lines(citation.excerpt, 438, "Helvetica-Oblique", 9.5)
        needed = len(citation_lines) * 14 + 52
        if y - needed < 68:
            page += 1
            y = _new_page(canvas, page)
        canvas.setFillColor(HexColor("#355F9E"))
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(54, y, f"SOURCE {index:02d}")
        canvas.setFillColor(HexColor("#17243A"))
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(116, y, _plain(citation.section)[:72])
        y -= 17
        canvas.setFillColor(HexColor("#657080"))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(116, y, _plain(citation.source_title)[:84])
        y -= 17
        canvas.setStrokeColor(HexColor("#C79D43"))
        canvas.setLineWidth(1.5)
        canvas.line(96, y + 3, 96, y - len(citation_lines) * 14 + 4)
        canvas.setFillColor(HexColor("#17243A"))
        y = _draw_wrapped(canvas, citation.excerpt, 116, y, 438, "Helvetica-Oblique", 9.5, 14)
        y -= 14

    canvas.setFillColor(HexColor("#657080"))
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(54, 36, "Research support only. Check every conclusion against its cited source.")
    canvas.drawRightString(558, 36, f"Report {report.report_id}")
    canvas.save()
    stream.seek(0)

    safe_ticker = "".join(character for character in report.ticker.upper() if character.isalnum() or character in {"-", "_"})
    return StreamingResponse(
        stream,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="edgar-lens-{safe_ticker}-research-brief.pdf"'},
    )

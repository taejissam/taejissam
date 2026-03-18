# check_outline.py
# 대상 파일: C:\Windows\System32\test.pdf

import sys
from dataclasses import dataclass
from typing import List

from pypdf import PdfReader
from pypdf.generic import ContentStream
from pdfminer.high_level import extract_text
import fitz  # PyMuPDF

PDF_PATH = r"D:\dev\data\260318_코딩아이_3-4 내지.pdf"

# PDF_PATH = r"C:\Windows\System32\test.pdf"
# 인터프리터 아나콘다 3.11.13(pdf2)

@dataclass
class PageReport:
    page_index: int
    has_text_ops: bool
    bt_blocks: int
    font_resources: bool
    mined_chars: int
    drawings: int
    verdict: str


def _pypdf_text_signals(reader: PdfReader, page_obj):
    has_text_ops = False
    bt_blocks = 0
    font_resources = False

    try:
        res = page_obj.get("/Resources")
        if res and res.get("/Font"):
            font_resources = True
    except Exception:
        pass

    try:
        contents = page_obj.get_contents()
        if contents is not None:
            cs = ContentStream(contents, reader)
            for operands, op in cs.operations:
                op = op if isinstance(op, bytes) else bytes(op, "latin1")
                if op == b"BT":
                    bt_blocks += 1
                if op in (b"Tj", b"TJ", b"'", b'"'):
                    has_text_ops = True
    except Exception:
        pass

    return has_text_ops, bt_blocks, font_resources


def _pdfminer_char_count(pdf_path: str, page_index: int) -> int:
    try:
        txt = extract_text(pdf_path, page_numbers=[page_index])
        return len(txt.strip()) if txt else 0
    except Exception:
        return 0


def _pymupdf_drawings(doc: fitz.Document, page_index: int) -> int:
    try:
        p = doc.load_page(page_index)
        return len(p.get_drawings())
    except Exception:
        return 0


def analyze_pdf(pdf_path: str) -> List[PageReport]:
    reader = PdfReader(pdf_path)
    doc = fitz.open(pdf_path)

    reports: List[PageReport] = []
    for i, page in enumerate(reader.pages):
        has_text_ops, bt_blocks, font_resources = _pypdf_text_signals(reader, page)
        mined_chars = _pdfminer_char_count(pdf_path, i)
        drawings = _pymupdf_drawings(doc, i)

        if (not has_text_ops) and mined_chars == 0:
            verdict = "텍스트 없음(아웃라인/이미지 가능성 높음)" if not font_resources \
                      else "텍스트 미표시 추정(아웃라인 또는 비표준 텍스트)"
        else:
            verdict = "실제 텍스트 있음(완전 아웃라인 아님)"

        reports.append(PageReport(
            page_index=i + 1,
            has_text_ops=has_text_ops,
            bt_blocks=bt_blocks,
            font_resources=font_resources,
            mined_chars=mined_chars,
            drawings=drawings,
            verdict=verdict
        ))
    doc.close()
    return reports


def print_summary(reports: List[PageReport]):
    total = len(reports)
    no_text_pages = sum(1 for r in reports if "텍스트 없음" in r.verdict)

    print("페이지별 결과")
    for r in reports:
        print(f"- p{r.page_index:>3}: "
              f"text_ops={r.has_text_ops}, BT={r.bt_blocks}, fonts={r.font_resources}, "
              f"chars(pdfminer)={r.mined_chars}, drawings={r.drawings} -> {r.verdict}")

    print("\n요약")
    if no_text_pages == total:
        print(f"전체 {total}쪽 모두 텍스트 없음 → 전면 아웃라인/이미지 PDF 추정")
    elif no_text_pages == 0:
        print(f"전체 {total}쪽 모두 텍스트 존재 → 아웃라인 처리되지 않음")
    else:
        print(f"혼합: 텍스트 없는 페이지 {no_text_pages}/{total}쪽 → 일부 페이지만 아웃라인/이미지")


if __name__ == "__main__":
    # 고정 경로 검사. 필요 시 다른 파일을 인수로 받아도 됩니다.
    path = PDF_PATH if len(sys.argv) < 2 else sys.argv[1]
    reports = analyze_pdf(path)
    print_summary(reports)

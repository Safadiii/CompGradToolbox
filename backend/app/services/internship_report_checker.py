# backend/app/services/internship_report_checker.py

import os
import re
import json
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import pypdfium2 as pdfium

DPI = 220

LABEL_PATTERNS = [
    r"\bsignature\b",
    r"\bsupervisor\b.*\bsignature\b",
    r"\bemployer\b.*\bsignature\b",
    r"\bmanager\b.*\bsignature\b",
    r"\bmentor\b.*\bsignature\b",
    r"\bstudent\b.*\bsignature\b",
]
NEGATIVE_LABEL_PATTERNS = [
    r"\bdigital\s+signature\b",
    r"\be-?signature\b",
]

POS_PATTERNS = [re.compile(p, re.IGNORECASE) for p in LABEL_PATTERNS]
NEG_PATTERNS = [re.compile(p, re.IGNORECASE) for p in NEGATIVE_LABEL_PATTERNS]

RIGHT_ROI_W_FRAC = 0.60
RIGHT_ROI_H_MULT = 3.2
RIGHT_ROI_Y_PAD_MULT = 1.0

BELOW_ROI_W_FRAC_OF_PAGE = 0.75
BELOW_ROI_H_MULT = 9.0
BELOW_ROI_Y_GAP_MULT = 0.6

MIN_BBOX_AREA = 250
MAX_BBOX_AREA = 300_000
MAX_KEEP_PER_ROI = 1


def render_page(pdf: pdfium.PdfDocument, page_idx: int, dpi: int) -> np.ndarray:
    scale = dpi / 72.0
    page = pdf[page_idx]
    bitmap = page.render(scale=scale)
    img = bitmap.to_numpy()
    if img.shape[2] == 4:
        img = img[:, :, :3]
    return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)


def _normalize_quotes(s: str) -> str:
    return (s.replace("’", "'")
             .replace("‘", "'")
             .replace("“", '"')
             .replace("”", '"'))


def _text_matches_label(text: str) -> bool:
    t = _normalize_quotes(text.strip())
    if not t:
        return False
    for neg in NEG_PATTERNS:
        if neg.search(t):
            return False
    return any(p.search(t) for p in POS_PATTERNS)


def pdf_box_to_pixel_box(box_pdf, page_h_pts, scale):
    l, b, r, t = box_pdf
    x1 = int(round(l * scale))
    x2 = int(round(r * scale))
    y1 = int(round((page_h_pts - t) * scale))
    y2 = int(round((page_h_pts - b) * scale))
    x = min(x1, x2)
    y = min(y1, y2)
    w = max(1, abs(x2 - x1))
    h = max(1, abs(y2 - y1))
    return x, y, w, h


def find_label_boxes_pdf_coords(page: pdfium.PdfPage) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    textpage = page.get_textpage()
    n = textpage.count_rects()
    for i in range(n):
        rect = textpage.get_rect(i)
        try:
            txt = textpage.get_text_bounded(*rect)
        except Exception:
            continue
        txt = (txt or "").strip()
        if not txt:
            continue
        if _text_matches_label(txt):
            hits.append({"text": txt, "box_pdf": rect})
    return hits


def _binarize(gray: np.ndarray) -> np.ndarray:
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    bw = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31, 10
    )
    return bw


def _remove_table_lines(bw: np.ndarray) -> np.ndarray:
    h, w = bw.shape
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(30, w // 25), 1))
    h_lines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, h_kernel, iterations=1)

    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(30, h // 25)))
    v_lines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, v_kernel, iterations=1)

    lines = cv2.bitwise_or(h_lines, v_lines)
    cleaned = cv2.bitwise_and(bw, cv2.bitwise_not(lines))
    return cleaned


def _component_candidates(mask: np.ndarray, max_keep: int) -> List[Tuple[float, int, int, int, int]]:
    num, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    cands: List[Tuple[float, int, int, int, int]] = []

    for i in range(1, num):
        x, y, w, h, area = stats[i]
        bbox_area = w * h
        if bbox_area <= 0:
            continue
        if area < MIN_BBOX_AREA or area > MAX_BBOX_AREA:
            continue
        fill = area / float(bbox_area)
        if fill > 0.75:
            continue
        score = float(area) * float(fill)
        cands.append((score, x, y, w, h))

    cands.sort(key=lambda t: t[0], reverse=True)
    return cands[:max_keep]


def build_rois_for_label(lx: int, ly: int, lw: int, lh: int, page_w: int, page_h: int):
    rx = lx + lw
    ry = int(max(0, ly - (RIGHT_ROI_Y_PAD_MULT * lh)))
    rw = int(max(1, (page_w - rx) * RIGHT_ROI_W_FRAC))
    rh = int(min(page_h - ry, max(1, lh * RIGHT_ROI_H_MULT)))

    bx = int(max(0, lx))
    by = int(min(page_h - 1, ly + lh + (BELOW_ROI_Y_GAP_MULT * lh)))
    bw = int(min(page_w - bx, page_w * BELOW_ROI_W_FRAC_OF_PAGE))
    bh = int(min(page_h - by, max(1, lh * BELOW_ROI_H_MULT)))

    # clamp
    rx = max(0, min(page_w - 1, rx))
    ry = max(0, min(page_h - 1, ry))
    rw = max(1, min(page_w - rx, rw))
    rh = max(1, min(page_h - ry, rh))

    bx = max(0, min(page_w - 1, bx))
    by = max(0, min(page_h - 1, by))
    bw = max(1, min(page_w - bx, bw))
    bh = max(1, min(page_h - by, bh))

    return (rx, ry, rw, rh), (bx, by, bw, bh)


def detect_signature_in_roi(gray: np.ndarray, x: int, y: int, w: int, h: int) -> Dict[str, Any]:
    roi = gray[y:y+h, x:x+w]
    bw = _binarize(roi)
    bw = _remove_table_lines(bw)
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)

    cands = _component_candidates(bw, max_keep=MAX_KEEP_PER_ROI)
    candidates = [{
        "score": float(score),
        "bbox_px": [int(x + cx), int(y + cy), int(cw), int(ch)]
    } for (score, cx, cy, cw, ch) in cands]

    return {"found": len(candidates) > 0, "candidates": candidates, "mask": bw}


def run_internship_checker(pdf_path: str, debug: bool = False) -> Dict[str, Any]:
    """
    Default: returns JSON only, writes nothing to disk.
    If debug=True: saves masks + report.json into a temp folder and returns debug.out_dir.
    """
    out_dir: Optional[str] = None
    if debug:
        out_dir = tempfile.mkdtemp(prefix="comp291_dbg_")
        os.makedirs(out_dir, exist_ok=True)

    pdf = pdfium.PdfDocument(pdf_path)
    scale = DPI / 72.0
    page_count = len(pdf)

    report: Dict[str, Any] = {
        "ok": True,
        "checker": "comp291-391",
        "file": os.path.basename(pdf_path),
        "mode": "LABEL_ROI_SCAN",
        "overall_status": "NOT_FOUND",
        "pages": [],
    }
    if debug:
        report["debug"] = {"out_dir": out_dir}

    def save_mask(name: str, mask: np.ndarray):
        if debug and out_dir:
            cv2.imwrite(os.path.join(out_dir, name), mask)

    overall_found = False

    for pidx in range(page_count):
        page = pdf[pidx]
        page_h_pts = float(page.get_height())

        bgr = render_page(pdf, pidx, DPI)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        H, W = gray.shape

        hits = find_label_boxes_pdf_coords(page)
        page_entry = {"page": pidx + 1, "page_status": "NOT_FOUND", "hits": []}

        if not hits:
            report["pages"].append(page_entry)
            continue

        for hit_i, hit in enumerate(hits, start=1):
            lx, ly, lw, lh = pdf_box_to_pixel_box(hit["box_pdf"], page_h_pts, scale)
            (rx, ry, rw, rh), (bx, by, bw, bh) = build_rois_for_label(lx, ly, lw, lh, W, H)

            right = detect_signature_in_roi(gray, rx, ry, rw, rh)
            below = detect_signature_in_roi(gray, bx, by, bw, bh)
            found = right["found"] or below["found"]

            candidates = []
            if right["found"]:
                for c in right["candidates"]:
                    candidates.append({"where": "RIGHT", **c})
            if below["found"]:
                for c in below["candidates"]:
                    candidates.append({"where": "BELOW", **c})

            page_entry["hits"].append({
                "label_or_pattern": hit["text"],
                "hit_index": hit_i,
                "status": "FOUND" if found else "NOT_FOUND",
                "label_box_px": [int(lx), int(ly), int(lw), int(lh)],
                "right_roi_px": [int(rx), int(ry), int(rw), int(rh)],
                "below_roi_px": [int(bx), int(by), int(bw), int(bh)],
                "candidates": candidates,
            })

            if debug:
                save_mask(f"p{pidx+1}_hit{hit_i}_mask_right.png", right["mask"])
                save_mask(f"p{pidx+1}_hit{hit_i}_mask_below.png", below["mask"])

            if found:
                overall_found = True
                page_entry["page_status"] = "FOUND"

        report["pages"].append(page_entry)

    report["overall_status"] = "FOUND" if overall_found else "NOT_FOUND"

    if debug and out_dir:
        with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    return report

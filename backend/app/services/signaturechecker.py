# backend/app/services/signature_checker.py

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
    r"\bsignature\s+of\b",
    r"\b(supervisor|student|adviser|advisor)\b.*\bsignature\b",
    r"\bsignature\b.*\b(supervisor|student|adviser|advisor)\b",
]
NEGATIVE_LABEL_PATTERNS = [
    r"\bdigital\s+signature\b",
    r"\be-?signature\b",
]

POS_PATTERNS = [re.compile(p, re.IGNORECASE) for p in LABEL_PATTERNS]
NEG_PATTERNS = [re.compile(p, re.IGNORECASE) for p in NEGATIVE_LABEL_PATTERNS]

# Policy:
# 1) Check first+last pages for signature label hits.
# 2) If found -> ONLY check ROIs near those labels and return result.
# 3) If no label hits -> fallback scan all pages (helps when no text-layer label exists).
FALLBACK_SCAN_ALL_PAGES_IF_NO_FIELD = True

# ROI geometry
RIGHT_ROI_W_FRAC = 0.60
RIGHT_ROI_H_MULT = 3.2
RIGHT_ROI_Y_PAD_MULT = 1.0

BELOW_ROI_W_FRAC_OF_PAGE = 0.75
BELOW_ROI_H_MULT = 9.0
BELOW_ROI_Y_GAP_MULT = 0.6

# Candidate filtering
MIN_BBOX_AREA = 250
MAX_BBOX_AREA = 300_000
MAX_KEEP_PER_ROI = 2
MAX_KEEP_PER_PAGE_FALLBACK = 3

# New: discard “signature candidates” that overlap actual PDF text
TEXT_OVERLAP_REJECT_THRESHOLD = 0.15  # 15% overlap of candidate area
# (raise to be stricter, lower to be more permissive)


# ----------------------------
# PDF render + text helpers
# ----------------------------
def render_page(pdf: pdfium.PdfDocument, page_idx: int, dpi: int) -> np.ndarray:
    scale = dpi / 72.0
    page = pdf[page_idx]
    bitmap = page.render(scale=scale)
    img = bitmap.to_numpy()
    if img.shape[2] == 4:
        img = img[:, :, :3]
    return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)


def _normalize_quotes(s: str) -> str:
    return (
        s.replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
    )


def _text_matches_label(text: str) -> bool:
    t = _normalize_quotes(text.strip())
    if not t:
        return False
    for neg in NEG_PATTERNS:
        if neg.search(t):
            return False
    return any(p.search(t) for p in POS_PATTERNS)


def pdf_box_to_pixel_box(box_pdf, page_h_pts, scale):
    """PDF box (l,b,r,t) points -> pixel box (x,y,w,h) top-left origin."""
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
    """
    Find label hits from text layer.
    Returns list: { "text": "...", "box_pdf": (l,b,r,t) }
    """
    hits: List[Dict[str, Any]] = []
    textpage = page.get_textpage()
    n = textpage.count_rects()
    for i in range(n):
        rect = textpage.get_rect(i)  # (l,b,r,t)
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


def collect_text_rects_px(page: pdfium.PdfPage, page_h_pts: float, scale: float) -> List[Tuple[int, int, int, int]]:
    """
    Collect all text rects on page (pixel coords) so we can reject candidates that overlap typed text.
    """
    rects: List[Tuple[int, int, int, int]] = []
    textpage = page.get_textpage()
    n = textpage.count_rects()
    for i in range(n):
        r = textpage.get_rect(i)  # (l,b,r,t)
        x, y, w, h = pdf_box_to_pixel_box(r, page_h_pts, scale)
        rects.append((x, y, w, h))
    return rects


def _overlap_ratio(boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
    ax, ay, aw, ah = boxA
    bx, by, bw, bh = boxB
    x1 = max(ax, bx)
    y1 = max(ay, by)
    x2 = min(ax + aw, bx + bw)
    y2 = min(ay + ah, by + bh)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    areaA = aw * ah
    return inter / areaA if areaA > 0 else 0.0


def candidate_overlaps_text(candidate_bbox: Tuple[int, int, int, int], text_rects: List[Tuple[int, int, int, int]]) -> bool:
    for tr in text_rects:
        if _overlap_ratio(candidate_bbox, tr) >= TEXT_OVERLAP_REJECT_THRESHOLD:
            return True
    return False


# ----------------------------
# Image processing / detection
# ----------------------------
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
    """
    Return list of candidates: (score, x, y, w, h)
    score favors larger & moderately sparse stroke blobs.
    """
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
        # avoid solid blocks
        if fill > 0.75:
            continue

        score = float(area) * float(fill)
        cands.append((score, x, y, w, h))

    cands.sort(key=lambda t: t[0], reverse=True)
    return cands[:max_keep]


def detect_signature_in_roi(
    gray: np.ndarray,
    roi_x: int,
    roi_y: int,
    roi_w: int,
    roi_h: int,
    text_rects_px: List[Tuple[int, int, int, int]],
) -> Dict[str, Any]:
    """
    Detect signature-like blobs inside ROI, rejecting candidates that overlap typed PDF text.
    Returns: { found, candidates, mask }
    """
    roi = gray[roi_y:roi_y + roi_h, roi_x:roi_x + roi_w]
    bw = _binarize(roi)
    bw = _remove_table_lines(bw)
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)

    cands = _component_candidates(bw, max_keep=MAX_KEEP_PER_ROI)

    candidates = []
    for (score, cx, cy, cw, ch) in cands:
        bbox_global = (int(roi_x + cx), int(roi_y + cy), int(cw), int(ch))
        # NEW: reject if overlaps selectable text
        if text_rects_px and candidate_overlaps_text(bbox_global, text_rects_px):
            continue
        candidates.append({
            "score": float(score),
            "bbox_px": [bbox_global[0], bbox_global[1], bbox_global[2], bbox_global[3]],
        })

    return {"found": len(candidates) > 0, "candidates": candidates, "mask": bw}


def detect_signature_fallback(
    gray: np.ndarray,
    text_rects_px: List[Tuple[int, int, int, int]],
) -> Dict[str, Any]:
    """
    Fallback full-page scan, still rejecting candidates overlapping typed text.
    """
    bw = _binarize(gray)
    bw = _remove_table_lines(bw)
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)

    cands = _component_candidates(bw, max_keep=MAX_KEEP_PER_PAGE_FALLBACK)

    candidates = []
    for (score, x, y, w, h) in cands:
        bbox = (int(x), int(y), int(w), int(h))
        if text_rects_px and candidate_overlaps_text(bbox, text_rects_px):
            continue
        candidates.append({
            "score": float(score),
            "bbox_px": [bbox[0], bbox[1], bbox[2], bbox[3]],
        })

    return {"found": len(candidates) > 0, "candidates": candidates, "mask": bw}


# ----------------------------
# ROI builders
# ----------------------------
def build_rois_for_label(lx: int, ly: int, lw: int, lh: int, page_w: int, page_h: int):
    # Right ROI
    rx = lx + lw
    ry = int(max(0, ly - (RIGHT_ROI_Y_PAD_MULT * lh)))
    rw = int(max(1, (page_w - rx) * RIGHT_ROI_W_FRAC))
    rh = int(min(page_h - ry, max(1, lh * RIGHT_ROI_H_MULT)))

    # Below ROI (kept, as requested)
    bx = int(max(0, lx))
    by = int(min(page_h - 1, ly + lh + (BELOW_ROI_Y_GAP_MULT * lh)))
    bw = int(min(page_w - bx, page_w * BELOW_ROI_W_FRAC_OF_PAGE))
    bh = int(min(page_h - by, max(1, lh * BELOW_ROI_H_MULT)))

    # Clamp
    rx = max(0, min(page_w - 1, rx))
    ry = max(0, min(page_h - 1, ry))
    rw = max(1, min(page_w - rx, rw))
    rh = max(1, min(page_h - ry, rh))

    bx = max(0, min(page_w - 1, bx))
    by = max(0, min(page_h - 1, by))
    bw = max(1, min(page_w - bx, bw))
    bh = max(1, min(page_h - by, bh))

    return (rx, ry, rw, rh), (bx, by, bw, bh)


# ----------------------------
# Main callable
# ----------------------------
def run_signature_checker(pdf_path: str, debug: bool = False) -> Dict[str, Any]:
    """
    Default: returns JSON only, writes nothing to disk.
    If debug=True: writes masks + report.json into a temp folder and returns debug.out_dir.
    """
    out_dir: Optional[str] = None
    if debug:
        out_dir = tempfile.mkdtemp(prefix="comp590_dbg_")
        os.makedirs(out_dir, exist_ok=True)

    def save_mask(name: str, mask: np.ndarray):
        if debug and out_dir:
            cv2.imwrite(os.path.join(out_dir, name), mask)

    pdf = pdfium.PdfDocument(pdf_path)
    scale = DPI / 72.0
    page_count = len(pdf)

    first_idx = 0
    last_idx = max(0, page_count - 1)
    priority_indices = [first_idx] + ([last_idx] if last_idx != first_idx else [])

    # Check label hits on first/last
    priority_hits = []
    any_field_found = False
    for pidx in priority_indices:
        page = pdf[pidx]
        hits = find_label_boxes_pdf_coords(page)
        priority_hits.append((pidx, hits))
        if hits:
            any_field_found = True

    report: Dict[str, Any] = {
        "ok": True,
        "checker": "comp590",
        "file": os.path.basename(pdf_path),
        "mode": "FIELD_FIRST_LAST_ONLY" if any_field_found else "NO_FIELD_FALLBACK",
        "overall_status": "NOT_FOUND",
        "pages": [],
    }
    if debug:
        report["debug"] = {"out_dir": out_dir}

    overall_found = False

    # Case A: Field found on first/last -> ONLY evaluate those pages/labels
    if any_field_found:
        for (pidx, hits) in priority_hits:
            page = pdf[pidx]
            page_h_pts = float(page.get_height())
            text_rects_px = collect_text_rects_px(page, page_h_pts, scale)

            bgr = render_page(pdf, pidx, DPI)
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            H, W = gray.shape

            page_entry = {"page": pidx + 1, "page_status": "NOT_FOUND", "hits": []}

            for hit_i, hit in enumerate(hits, start=1):
                lx, ly, lw, lh = pdf_box_to_pixel_box(hit["box_pdf"], page_h_pts, scale)
                (rx, ry, rw, rh), (bx, by, bw, bh) = build_rois_for_label(lx, ly, lw, lh, W, H)

                right = detect_signature_in_roi(gray, rx, ry, rw, rh, text_rects_px)
                below = detect_signature_in_roi(gray, bx, by, bw, bh, text_rects_px)

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

    # Case B: No field on first/last -> fallback scan
    indices = list(range(page_count)) if FALLBACK_SCAN_ALL_PAGES_IF_NO_FIELD else priority_indices

    for pidx in indices:
        page = pdf[pidx]
        page_h_pts = float(page.get_height())
        text_rects_px = collect_text_rects_px(page, page_h_pts, scale)

        bgr = render_page(pdf, pidx, DPI)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        fb = detect_signature_fallback(gray, text_rects_px)

        if debug:
            save_mask(f"p{pidx+1}_fallback_mask.png", fb["mask"])

        page_entry = {
            "page": pidx + 1,
            "page_status": "FOUND" if fb["found"] else "NOT_FOUND",
            "hits": [{
                "label_or_pattern": None,
                "hit_index": 1,
                "status": "FOUND" if fb["found"] else "NOT_FOUND",
                "label_box_px": None,
                "right_roi_px": None,
                "below_roi_px": None,
                "candidates": [{"where": "FALLBACK", **c} for c in fb["candidates"]],
            }],
        }

        if fb["found"]:
            overall_found = True

        report["pages"].append(page_entry)

    report["overall_status"] = "FOUND" if overall_found else "NOT_FOUND"

    if debug and out_dir:
        with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    return report

import io
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import docx
import fitz
import pdfplumber
from PIL import Image, ImageSequence

from backend.app.config import get_extraction_config
from backend.app.services.extraction.ocr.base import (
    OcrEngineUnavailableError,
    detect_script_guess,
    get_ocr_provider,
)
from backend.app.services.extraction.ocr.preprocess import (
    assess_image_quality,
    extract_exif_and_hashes,
    preprocess_for_ocr,
)

DEVANAGARI_REGEX = re.compile(r"[\u0900-\u097F]")

_GLOBAL_OCR_INSTANCE = None


def get_rapid_ocr():
    global _GLOBAL_OCR_INSTANCE
    if _GLOBAL_OCR_INSTANCE is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _GLOBAL_OCR_INSTANCE = RapidOCR()
        except Exception:
            return None
    return _GLOBAL_OCR_INSTANCE


def run_rapid_ocr(img_input) -> str:
    """Legacy helper retained for backward compatibility."""
    try:
        import numpy as np

        ocr = get_rapid_ocr()
        if ocr is None:
            return ""
        if isinstance(img_input, (str, Path)):
            img = Image.open(str(img_input)).convert("RGB")
        else:
            img = img_input.convert("RGB")
        result, _ = ocr(np.array(img))
        if not result:
            return ""
        lines = [item[1] for item in result if item and len(item) > 1 and item[1].strip()]
        return "\n".join(lines)
    except Exception:
        return ""


def compute_span_bbox(
    words: List[Dict[str, Any]],
    rel_start: int,
    rel_end: int,
) -> Optional[List[int]]:
    """
    Computes the union bounding box [x0, y0, x1, y1] of all word boxes on a page
    whose character span [char_start, char_end) overlaps [rel_start, rel_end).
    """
    if not words or rel_end <= rel_start:
        return None
    matching_boxes = []
    for w in words:
        w_start = w.get("char_start")
        w_end = w.get("char_end")
        bbox = w.get("bbox")
        if w_start is None or w_end is None or not bbox or len(bbox) < 4:
            continue
        if max(rel_start, int(w_start)) < min(rel_end, int(w_end)):
            matching_boxes.append(bbox)

    if not matching_boxes:
        return None
    x0 = min(int(round(b[0])) for b in matching_boxes)
    y0 = min(int(round(b[1])) for b in matching_boxes)
    x1 = max(int(round(b[2])) for b in matching_boxes)
    y1 = max(int(round(b[3])) for b in matching_boxes)
    return [x0, y0, x1, y1]


def _extract_pymupdf_text_layer_words(page: fitz.Page, page_no: int) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Extracts structured words with bounding boxes from a digital PDF text layer via PyMuPDF
    and reconstructs full page text with exact char_start/char_end offsets.
    """
    raw_words = page.get_text("words") or []
    # raw_words items: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
    if not raw_words:
        return "", []

    lines_out: List[str] = []
    words_out: List[Dict[str, Any]] = []
    current_line_key = None
    cursor = 0

    for idx, item in enumerate(raw_words):
        x0, y0, x1, y1, token, block_no, line_no, _ = item[:8]
        token_str = str(token).strip()
        if not token_str:
            continue
        line_key = f"{block_no}_{line_no}"
        if current_line_key is not None and line_key != current_line_key:
            lines_out.append("\n")
            cursor += 1
        elif current_line_key is not None:
            lines_out.append(" ")
            cursor += 1
        current_line_key = line_key

        start_pos = cursor
        lines_out.append(token_str)
        cursor += len(token_str)
        end_pos = cursor

        words_out.append({
            "word_id": f"p{page_no}_w{idx + 1}",
            "text": token_str,
            "conf": 1.0,
            "bbox": [int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))],
            "page": page_no,
            "line_id": line_key,
            "script_guess": detect_script_guess(token_str),
            "char_start": start_pos,
            "char_end": end_pos,
        })

    return "".join(lines_out), words_out


def _process_raster_page(
    pil_img: Image.Image,
    page_no: int,
    dpi_hint: Optional[int] = None,
    officer_marked_handwritten: bool = False,
) -> Dict[str, Any]:
    """
    Runs the OpenCV quality gate, EXIF/phash extraction, preprocessing, and OCR provider
    on a single raster page image.
    """
    meta = extract_exif_and_hashes(pil_img)
    quality = assess_image_quality(pil_img, dpi_hint=dpi_hint)

    if not quality["passed"]:
        return {
            "page_no": page_no,
            "page_or_paragraph": f"Page {page_no} (Needs Better Image)",
            "source_kind": "ocr_handwritten" if officer_marked_handwritten else "ocr_printed",
            "status": "needs_better_image",
            "quality_reason": quality["reason"],
            "quality_metrics": quality["metrics"],
            "preprocess_params": {},
            "text": "",
            "words": [],
            "mean_confidence": 0.0,
            "is_handwritten": bool(officer_marked_handwritten),
            "engine_name": "quality_gate",
            "engine_version": "1.0",
            "page_image_sha256": meta["page_image_sha256"],
            "perceptual_hash": meta["perceptual_hash"],
            "exif": meta["exif"],
            "error": None,
        }

    prep_img, prep_params = preprocess_for_ocr(pil_img, quality["metrics"])
    provider = get_ocr_provider()
    stroke_cv = float(quality["metrics"].get("stroke_uniformity_cv", 0.0))

    try:
        ocr_res = provider.recognize_page(
            image=prep_img,
            page=page_no,
            officer_marked_handwritten=officer_marked_handwritten,
            stroke_uniformity_cv=stroke_cv,
        )
    except OcrEngineUnavailableError as exc:
        return {
            "page_no": page_no,
            "page_or_paragraph": f"Page {page_no} (OCR Unavailable)",
            "source_kind": "ocr_handwritten" if officer_marked_handwritten else "ocr_printed",
            "status": "ocr_unavailable",
            "quality_reason": str(exc),
            "quality_metrics": quality["metrics"],
            "preprocess_params": prep_params,
            "text": "",
            "words": [],
            "mean_confidence": 0.0,
            "is_handwritten": bool(officer_marked_handwritten),
            "engine_name": provider.engine_name,
            "engine_version": provider.engine_version,
            "page_image_sha256": meta["page_image_sha256"],
            "perceptual_hash": meta["perceptual_hash"],
            "exif": meta["exif"],
            "error": str(exc),
            "reason_code": exc.reason_code,
        }

    ocr_cfg = get_extraction_config().get("ocr", {})
    review_below = float(ocr_cfg.get("review_below_conf", 0.75))
    is_hw = bool(ocr_res["is_handwritten"])
    mean_conf = float(ocr_res["mean_confidence"])
    page_status = "pending_review" if (is_hw or mean_conf < review_below) else "ready"

    return {
        "page_no": page_no,
        "page_or_paragraph": f"Page {page_no} (OCR{' Handwritten' if is_hw else ''})",
        "source_kind": ocr_res["source_kind"],
        "status": page_status,
        "quality_reason": None,
        "quality_metrics": quality["metrics"],
        "preprocess_params": prep_params,
        "text": ocr_res["full_text"],
        "words": ocr_res["words"],
        "mean_confidence": mean_conf,
        "is_handwritten": is_hw,
        "engine_name": ocr_res["engine_name"],
        "engine_version": ocr_res["engine_version"],
        "page_image_sha256": meta["page_image_sha256"],
        "perceptual_hash": meta["perceptual_hash"],
        "exif": meta["exif"],
        "error": None,
    }


def read_document_text(
    file_path: str,
    officer_marked_handwritten: bool = False,
    use_cache: bool = False,
) -> Dict[str, Any]:
    """
    Extracts structured text and per-word bounding-box provenance from:
      - PDFs (page-by-page routing: PyMuPDF digital text layer if >= text_layer_min_chars,
        otherwise rendered at render_dpi and processed through OpenCV quality gate + OCR)
      - Images (.png, .jpg, .jpeg, .webp, .bmp, .tiff, .tif) with EXIF, phash, quality gate & OCR
      - DOCX and TXT documents
    """
    p = Path(file_path)
    if not p.exists():
        return {
            "pages": [],
            "full_text": "",
            "warning": None,
            "error": f"File not found: {file_path}",
        }

    ext = p.suffix.lower()
    pages_data: List[Dict[str, Any]] = []
    full_text = ""
    warning = None
    ext_cfg = get_extraction_config()
    pdf_cfg = ext_cfg.get("pdf", {})
    min_text_chars = int(pdf_cfg.get("text_layer_min_chars", 40))
    render_dpi = int(pdf_cfg.get("render_dpi", 250))

    # 1. PDF Extraction (Page-by-Page Text Layer vs OCR Routing)
    if ext == ".pdf":
        try:
            # First try opening via PyMuPDF (fitz) for mixed digital/scanned page routing
            try:
                fitz_doc = fitz.open(file_path)
            except Exception:
                fitz_doc = None

            if fitz_doc is not None and len(fitz_doc) > 0:
                char_cursor = 0
                ocr_errors: List[str] = []
                quality_failures: List[str] = []

                for page_idx in range(len(fitz_doc)):
                    page_no = page_idx + 1
                    f_page = fitz_doc[page_idx]
                    tl_text, tl_words = _extract_pymupdf_text_layer_words(f_page, page_no)

                    if len(tl_text.strip()) >= min_text_chars and not officer_marked_handwritten:
                        pages_data.append({
                            "page_no": page_no,
                            "page_or_paragraph": f"Page {page_no}",
                            "source_kind": "text_layer_pdf",
                            "status": "ready",
                            "quality_reason": None,
                            "quality_metrics": {"text_layer_chars": len(tl_text.strip())},
                            "preprocess_params": {},
                            "text": tl_text,
                            "words": tl_words,
                            "mean_confidence": 1.0,
                            "is_handwritten": False,
                            "engine_name": "pymupdf",
                            "engine_version": getattr(fitz, "__doc__", "1.24")[:16] if getattr(fitz, "__doc__", None) else "pymupdf",
                            "page_image_sha256": None,
                            "perceptual_hash": None,
                            "exif": {"disclaimer": "as reported by file"},
                            "char_offset": char_cursor,
                        })
                        char_cursor += len(tl_text) + 2
                    else:
                        # Render page at config DPI and run quality gate + OCR
                        pix = f_page.get_pixmap(dpi=render_dpi)
                        pil_img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
                        ocr_page = _process_raster_page(
                            pil_img=pil_img,
                            page_no=page_no,
                            dpi_hint=render_dpi,
                            officer_marked_handwritten=officer_marked_handwritten,
                        )
                        ocr_page["char_offset"] = char_cursor
                        if ocr_page.get("error"):
                            ocr_errors.append(ocr_page["error"])
                        if ocr_page.get("status") == "needs_better_image" and ocr_page.get("quality_reason"):
                            quality_failures.append(f"Page {page_no}: {ocr_page['quality_reason']}")
                        if ocr_page.get("text"):
                            char_cursor += len(ocr_page["text"]) + 2
                        elif tl_text.strip():
                            # Short digital text layer when OCR is unavailable
                            ocr_page["text"] = tl_text.strip()
                            ocr_page["words"] = tl_words
                            ocr_page["source_kind"] = "text_layer_pdf"
                            ocr_page["status"] = "ready"
                            ocr_page["error"] = None
                            char_cursor += len(tl_text.strip()) + 2
                        pages_data.append(ocr_page)

                fitz_doc.close()
                full_text = "\n\n".join(pg["text"] for pg in pages_data if pg.get("text"))

                if not full_text.strip():
                    if quality_failures:
                        return {
                            "pages": pages_data,
                            "full_text": "",
                            "status": "needs_better_image",
                            "warning": "; ".join(quality_failures),
                            "error": None,
                        }
                    if ocr_errors:
                        return {
                            "pages": pages_data,
                            "full_text": "",
                            "status": "ocr_unavailable",
                            "warning": None,
                            "error": ocr_errors[0],
                        }
                    return {
                        "pages": pages_data,
                        "full_text": "",
                        "warning": None,
                        "error": "No readable text detected in PDF",
                    }
            else:
                # Fallback to pdfplumber when fitz cannot open (e.g. mocked pdfplumber in unit tests)
                with pdfplumber.open(file_path) as pdf:
                    char_cursor = 0
                    for page_idx, page in enumerate(pdf.pages, start=1):
                        p_text = (page.extract_text() or "").strip()
                        if p_text:
                            pages_data.append({
                                "page_no": page_idx,
                                "page_or_paragraph": f"Page {page_idx}",
                                "source_kind": "text_layer_pdf",
                                "status": "ready",
                                "quality_reason": None,
                                "quality_metrics": {"text_layer_chars": len(p_text)},
                                "preprocess_params": {},
                                "text": p_text,
                                "words": [],
                                "mean_confidence": 1.0,
                                "is_handwritten": False,
                                "engine_name": "pdfplumber",
                                "engine_version": "1.0",
                                "page_image_sha256": None,
                                "perceptual_hash": None,
                                "exif": {"disclaimer": "as reported by file"},
                                "char_offset": char_cursor,
                            })
                            char_cursor += len(p_text) + 2
                    full_text = "\n\n".join(pg["text"] for pg in pages_data)
                    if not full_text.strip():
                        return {
                            "pages": [],
                            "full_text": "",
                            "warning": None,
                            "error": "failed: scanned PDF — OCR not supported in this version",
                        }
        except Exception as exc:
            return {
                "pages": [],
                "full_text": "",
                "warning": None,
                "error": f"Failed to extract PDF: {str(exc)}",
            }

    # 2. DOCX Extraction
    elif ext == ".docx":
        try:
            doc = docx.Document(file_path)
            char_cursor = 0
            para_num = 1
            for para in doc.paragraphs:
                p_text = para.text.strip()
                if p_text:
                    pages_data.append({
                        "page_no": para_num,
                        "page_or_paragraph": f"Paragraph {para_num}",
                        "source_kind": "structured_file",
                        "status": "ready",
                        "quality_reason": None,
                        "quality_metrics": {},
                        "preprocess_params": {},
                        "text": p_text,
                        "words": [],
                        "mean_confidence": 1.0,
                        "is_handwritten": False,
                        "engine_name": "python-docx",
                        "engine_version": "1.0",
                        "page_image_sha256": None,
                        "perceptual_hash": None,
                        "exif": {"disclaimer": "as reported by file"},
                        "char_offset": char_cursor,
                    })
                    char_cursor += len(p_text) + 2
                    para_num += 1
            full_text = "\n\n".join(pg["text"] for pg in pages_data)
        except Exception as exc:
            return {
                "pages": [],
                "full_text": "",
                "warning": None,
                "error": f"Failed to extract DOCX: {str(exc)}",
            }

    # 3. Plain Text (.txt)
    elif ext in [".txt", ".text"]:
        raw_bytes = p.read_bytes()
        decoded_text = None
        for enc in ["utf-8", "utf-8-sig", "cp1252", "latin-1"]:
            try:
                decoded_text = raw_bytes.decode(enc)
                break
            except Exception:
                continue
        if decoded_text is None:
            decoded_text = raw_bytes.decode("utf-8", errors="replace")

        paras = [seg.strip() for seg in re.split(r"\n\s*\n", decoded_text) if seg.strip()]
        if not paras:
            paras = [decoded_text.strip()] if decoded_text.strip() else []

        char_cursor = 0
        for idx, para_text in enumerate(paras, start=1):
            pages_data.append({
                "page_no": idx,
                "page_or_paragraph": f"Paragraph {idx}",
                "source_kind": "structured_file",
                "status": "ready",
                "quality_reason": None,
                "quality_metrics": {},
                "preprocess_params": {},
                "text": para_text,
                "words": [],
                "mean_confidence": 1.0,
                "is_handwritten": False,
                "engine_name": "text_reader",
                "engine_version": "1.0",
                "page_image_sha256": None,
                "perceptual_hash": None,
                "exif": {"disclaimer": "as reported by file"},
                "char_offset": char_cursor,
            })
            char_cursor += len(para_text) + 2
        full_text = "\n\n".join(pg["text"] for pg in pages_data)

    # 4. Images & Scanned Photos (.png, .jpg, .jpeg, .webp, .bmp, .tiff, .tif)
    elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"]:
        try:
            with Image.open(file_path) as img_obj:
                frames = [frame.copy() for frame in ImageSequence.Iterator(img_obj)]
        except Exception as exc:
            return {
                "pages": [],
                "full_text": "",
                "warning": None,
                "error": f"Failed to open image file: {str(exc)}",
            }

        char_cursor = 0
        ocr_errors = []
        quality_failures = []

        for idx, frame in enumerate(frames, start=1):
            page_res = _process_raster_page(
                pil_img=frame,
                page_no=idx,
                officer_marked_handwritten=officer_marked_handwritten,
            )
            page_res["char_offset"] = char_cursor
            if page_res.get("error"):
                ocr_errors.append(page_res["error"])
            if page_res.get("status") == "needs_better_image" and page_res.get("quality_reason"):
                quality_failures.append(page_res["quality_reason"])
            if page_res.get("text"):
                char_cursor += len(page_res["text"]) + 2
            pages_data.append(page_res)

        full_text = "\n\n".join(pg["text"] for pg in pages_data if pg.get("text"))
        if not full_text.strip():
            if quality_failures:
                return {
                    "pages": pages_data,
                    "full_text": "",
                    "status": "needs_better_image",
                    "warning": "; ".join(quality_failures),
                    "error": None,
                }
            if ocr_errors:
                return {
                    "pages": pages_data,
                    "full_text": "",
                    "status": "ocr_unavailable",
                    "warning": None,
                    "error": ocr_errors[0],
                }
            return {
                "pages": pages_data,
                "full_text": "",
                "warning": None,
                "error": "No readable text detected in uploaded image",
            }
    else:
        return {
            "pages": [],
            "full_text": "",
            "warning": None,
            "error": f"Unsupported document format: {ext}",
        }

    if DEVANAGARI_REGEX.search(full_text):
        warning = "partially supported: Devanagari text ignored"

    overall_status = "ready"
    if any(pg.get("status") == "needs_better_image" for pg in pages_data) and not full_text.strip():
        overall_status = "needs_better_image"
    elif any(pg.get("status") == "pending_review" for pg in pages_data):
        overall_status = "pending_review"

    return {
        "pages": pages_data,
        "full_text": full_text,
        "status": overall_status,
        "warning": warning,
        "error": None,
    }

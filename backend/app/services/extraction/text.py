import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import pdfplumber
import docx

DEVANAGARI_REGEX = re.compile(r'[\u0900-\u097F]')

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
    """Runs RapidOCR on an image file path or PIL Image using cached instance."""
    try:
        import numpy as np
        from PIL import Image

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

def read_document_text(file_path: str) -> Dict[str, Any]:
    """
    Extracts text from PDF, DOCX, TXT narrative documents, or image photos (JPG/PNG).
    Preserves page numbers (PDF) or paragraph indices (DOCX/TXT).
    Performs OCR for scanned PDFs and image files via RapidOCR.
    """
    p = Path(file_path)
    if not p.exists():
        return {
            "pages": [],
            "full_text": "",
            "warning": None,
            "error": f"File not found: {file_path}"
        }

    ext = p.suffix.lower()
    pages_data: List[Dict[str, Any]] = []
    full_text = ""
    warning = None
    error = None

    # 1. PDF Extraction
    if ext == ".pdf":
        try:
            with pdfplumber.open(file_path) as pdf:
                char_cursor = 0
                for page_idx, page in enumerate(pdf.pages, start=1):
                    p_text = page.extract_text() or ""
                    # Keep clean line breaks
                    clean_text = p_text.strip()
                    if clean_text:
                        pages_data.append({
                            "page_or_paragraph": f"Page {page_idx}",
                            "text": clean_text,
                            "char_offset": char_cursor
                        })
                        char_cursor += len(clean_text) + 2

                full_text = "\n\n".join(pg["text"] for pg in pages_data)

                # Fallback to OCR if scanned PDF (no selectable text)
                if not full_text.strip():
                    try:
                        import pypdfium2
                        pdf_doc = pypdfium2.PdfDocument(str(file_path))
                        char_cursor = 0
                        for page_idx, page in enumerate(pdf_doc, start=1):
                            pil_img = page.render(scale=2.0).to_pil()
                            ocr_text = run_rapid_ocr(pil_img)
                            if ocr_text.strip():
                                pages_data.append({
                                    "page_or_paragraph": f"Page {page_idx} (OCR)",
                                    "text": ocr_text,
                                    "char_offset": char_cursor
                                })
                                char_cursor += len(ocr_text) + 2
                        full_text = "\n\n".join(pg["text"] for pg in pages_data)
                    except Exception as ocr_err:
                        return {
                            "pages": [],
                            "full_text": "",
                            "warning": None,
                            "error": f"Failed to OCR scanned PDF: {str(ocr_err)}"
                        }

                if not full_text.strip():
                    return {
                        "pages": [],
                        "full_text": "",
                        "warning": None,
                        "error": "No readable text detected in PDF"
                    }
        except Exception as e:
            return {
                "pages": [],
                "full_text": "",
                "warning": None,
                "error": f"Failed to extract PDF: {str(e)}"
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
                        "page_or_paragraph": f"Paragraph {para_num}",
                        "text": p_text,
                        "char_offset": char_cursor
                    })
                    char_cursor += len(p_text) + 2
                    para_num += 1

            full_text = "\n\n".join(pg["text"] for pg in pages_data)
        except Exception as e:
            return {
                "pages": [],
                "full_text": "",
                "warning": None,
                "error": f"Failed to extract DOCX: {str(e)}"
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

        # Split into paragraphs
        paras = [p.strip() for p in re.split(r'\n\s*\n', decoded_text) if p.strip()]
        if not paras:
            paras = [decoded_text.strip()] if decoded_text.strip() else []

        char_cursor = 0
        for idx, para_text in enumerate(paras, start=1):
            pages_data.append({
                "page_or_paragraph": f"Paragraph {idx}",
                "text": para_text,
                "char_offset": char_cursor
            })
            char_cursor += len(para_text) + 2

        full_text = "\n\n".join(pg["text"] for pg in pages_data)

    # 4. Images & Scanned Photos (.png, .jpg, .jpeg, .webp, .bmp, .tiff)
    elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
        ocr_text = run_rapid_ocr(file_path)
        if ocr_text.strip():
            pages_data.append({
                "page_or_paragraph": "Image Document (OCR)",
                "text": ocr_text,
                "char_offset": 0
            })
            full_text = ocr_text
        else:
            return {
                "pages": [],
                "full_text": "",
                "warning": None,
                "error": "No readable text detected in uploaded image"
            }

    else:
        return {
            "pages": [],
            "full_text": "",
            "warning": None,
            "error": f"Unsupported document format: {ext}"
        }

    # 4. Check Devanagari script presence
    if DEVANAGARI_REGEX.search(full_text):
        warning = "partially supported: Devanagari text ignored"

    return {
        "pages": pages_data,
        "full_text": full_text,
        "warning": warning,
        "error": None
    }

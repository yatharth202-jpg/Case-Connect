from abc import ABC, abstractmethod
import json
import os
from pathlib import Path
import re
import shutil
from typing import Any, Dict, List, Optional

from PIL import Image
import pytesseract
from sqlalchemy.orm import Session

from backend.app.audit.service import record_audit_log
from backend.app.config import get_extraction_config
from backend.app.db.sql import CaseSetting

DEVANAGARI_CHAR_RE = re.compile(r"[\u0900-\u097F]")
LATIN_CHAR_RE = re.compile(r"[A-Za-z]")
DIGIT_ONLY_RE = re.compile(r"^[\d\u0966-\u096F\W_]+$")


class OcrEngineUnavailableError(RuntimeError):
    """Raised when the configured local OCR binary (e.g. Tesseract) is missing or unreachable."""

    def __init__(self, message: str, reason_code: str = "ocr_binary_missing"):
        super().__init__(message)
        self.reason_code = reason_code


def detect_script_guess(text: str) -> str:
    """Heuristically classifies the script of a token or page text."""
    if not text or not text.strip():
        return "unknown"
    has_dev = bool(DEVANAGARI_CHAR_RE.search(text))
    has_lat = bool(LATIN_CHAR_RE.search(text))
    if has_dev and has_lat:
        return "mixed_hin_eng"
    if has_dev:
        return "devanagari"
    if has_lat:
        return "latin"
    if DIGIT_ONLY_RE.match(text.strip()):
        return "digits"
    return "latin"


def select_ocr_languages(script_hint: Optional[str] = None) -> List[str]:
    """Selects OCR languages from config based on optional script hint."""
    ocr_cfg = get_extraction_config().get("ocr", {})
    configured = list(ocr_cfg.get("languages") or ["eng", "hin"])
    if script_hint == "latin" and "eng" in configured:
        return ["eng"]
    if script_hint == "devanagari" and "hin" in configured:
        return ["hin", "eng"] if "eng" in configured else ["hin"]
    return configured


def classify_page_handwritten(
    mean_confidence: float,
    stroke_uniformity_cv: float,
    officer_marked_handwritten: bool = False,
) -> bool:
    """
    Classifies a page as handwritten vs printed using:
    1. Explicit officer flag (`officer_marked_handwritten=True`), OR
    2. Heuristic combining OCR mean confidence and stroke-width coefficient of variation
       against configurable thresholds in `extraction.ocr`.
    """
    if officer_marked_handwritten:
        return True
    ocr_cfg = get_extraction_config().get("ocr", {})
    conf_thresh = float(ocr_cfg.get("handwritten_mean_conf_threshold", 0.68))
    stroke_thresh = float(ocr_cfg.get("handwritten_stroke_cv_threshold", 0.55))
    if mean_confidence < conf_thresh and stroke_uniformity_cv >= stroke_thresh:
        return True
    return False


class OcrProvider(ABC):
    """Pluggable local OCR provider interface (Tesseract default; PaddleOCR/others swappable)."""

    engine_name: str = "base_ocr"
    engine_version: str = "1.0"

    @abstractmethod
    def recognize(
        self,
        image: Image.Image,
        page: int = 1,
        languages: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Runs OCR on a PIL Image and returns a list of word dicts:
        {word_id, text, conf, bbox: [x0, y0, x1, y1], page, line_id, script_guess, char_start, char_end}
        """
        raise NotImplementedError

    def recognize_page(
        self,
        image: Image.Image,
        page: int = 1,
        languages: Optional[List[str]] = None,
        officer_marked_handwritten: bool = False,
        stroke_uniformity_cv: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Recognizes a page, reconstructs line-aligned text with exact character spans per word,
        and applies handwriting classification & confidence capping from config.
        """
        ocr_cfg = get_extraction_config().get("ocr", {})
        hw_cap = float(ocr_cfg.get("handwritten_conf_cap", 0.65))

        raw_words = self.recognize(image=image, page=page, languages=languages)
        if not raw_words:
            is_hw = bool(officer_marked_handwritten)
            return {
                "words": [],
                "full_text": "",
                "mean_confidence": 0.0,
                "is_handwritten": is_hw,
                "source_kind": "ocr_handwritten" if is_hw else "ocr_printed",
                "engine_name": self.engine_name,
                "engine_version": self.engine_version,
                "script_guess": "unknown",
            }

        raw_mean_conf = sum(float(w.get("conf", 0.0)) for w in raw_words) / max(1, len(raw_words))
        is_hw = classify_page_handwritten(
            mean_confidence=raw_mean_conf,
            stroke_uniformity_cv=stroke_uniformity_cv,
            officer_marked_handwritten=officer_marked_handwritten,
        )

        # Reconstruct full_text line by line and assign exact char_start / char_end on each word
        lines_out: List[str] = []
        current_line_id = None
        cursor = 0
        words_with_spans: List[Dict[str, Any]] = []

        for idx, w in enumerate(raw_words):
            token = str(w.get("text", "")).strip()
            if not token:
                continue
            line_id = w.get("line_id", "1_1_1")
            if current_line_id is not None and line_id != current_line_id:
                lines_out.append("\n")
                cursor += 1
            elif current_line_id is not None:
                lines_out.append(" ")
                cursor += 1
            current_line_id = line_id

            start_pos = cursor
            lines_out.append(token)
            cursor += len(token)
            end_pos = cursor

            w_conf = float(w.get("conf", 0.0))
            if is_hw:
                w_conf = min(w_conf, hw_cap)

            words_with_spans.append({
                "word_id": w.get("word_id") or f"p{page}_w{idx + 1}",
                "text": token,
                "conf": round(w_conf, 4),
                "bbox": list(w.get("bbox") or [0, 0, 0, 0]),
                "page": int(w.get("page", page)),
                "line_id": str(line_id),
                "script_guess": w.get("script_guess") or detect_script_guess(token),
                "char_start": start_pos,
                "char_end": end_pos,
            })

        full_text = "".join(lines_out)
        effective_mean = (
            sum(w["conf"] for w in words_with_spans) / len(words_with_spans)
            if words_with_spans
            else 0.0
        )
        if is_hw:
            effective_mean = min(effective_mean, hw_cap)

        return {
            "words": words_with_spans,
            "full_text": full_text,
            "mean_confidence": round(effective_mean, 4),
            "is_handwritten": is_hw,
            "source_kind": "ocr_handwritten" if is_hw else "ocr_printed",
            "engine_name": self.engine_name,
            "engine_version": self.engine_version,
            "script_guess": detect_script_guess(full_text),
        }


class TesseractProvider(OcrProvider):
    """
    Local Tesseract OCR provider using `pytesseract.image_to_data` for word-level
    confidence scores and bounding boxes.
    """

    engine_name = "tesseract"

    def __init__(self):
        self.tesseract_cmd = self._resolve_tesseract_binary()
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        self.engine_version = self._detect_version()

    @staticmethod
    def _resolve_tesseract_binary() -> Optional[str]:
        ocr_cfg = get_extraction_config().get("ocr", {})
        env_key = str(ocr_cfg.get("tesseract_cmd_env", "TESSERACT_CMD"))
        env_val = os.environ.get(env_key) or ocr_cfg.get("tesseract_cmd")
        if env_val and Path(env_val).exists():
            return str(Path(env_val).resolve())

        which_val = shutil.which("tesseract")
        if which_val:
            return which_val

        # Common Windows installation paths for UB-Mannheim Tesseract
        candidates = [
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
            Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tesseract.exe",
            Path.home() / "AppData" / "Local" / "Tesseract-OCR" / "tesseract.exe",
        ]
        for cand in candidates:
            if cand.exists():
                return str(cand.resolve())
        return None

    def _detect_version(self) -> str:
        if not self.tesseract_cmd:
            return "unavailable"
        try:
            return str(pytesseract.get_tesseract_version())
        except Exception:
            return "unknown"

    def recognize(
        self,
        image: Image.Image,
        page: int = 1,
        languages: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        if not self.tesseract_cmd or not Path(self.tesseract_cmd).exists():
            ocr_cfg = get_extraction_config().get("ocr", {})
            env_key = str(ocr_cfg.get("tesseract_cmd_env", "TESSERACT_CMD"))
            raise OcrEngineUnavailableError(
                f"Local Tesseract OCR binary not found. Please install Tesseract OCR (with 'eng' and 'hin' language data) "
                f"or set the {env_key} environment variable to the tesseract executable path."
            )

        langs = languages or select_ocr_languages()
        lang_str = "+".join(langs)

        try:
            data = pytesseract.image_to_data(
                image,
                lang=lang_str,
                output_type=pytesseract.Output.DICT,
            )
        except pytesseract.TesseractError as exc:
            # Fallback to 'eng' if 'hin' traineddata is not installed yet
            if "hin" in langs and len(langs) > 1:
                try:
                    data = pytesseract.image_to_data(
                        image,
                        lang="eng",
                        output_type=pytesseract.Output.DICT,
                    )
                except Exception as inner_exc:
                    raise OcrEngineUnavailableError(
                        f"Tesseract OCR execution failed: {str(inner_exc)}",
                        reason_code="ocr_execution_failed",
                    )
            else:
                raise OcrEngineUnavailableError(
                    f"Tesseract OCR execution failed: {str(exc)}",
                    reason_code="ocr_execution_failed",
                )
        except Exception as exc:
            raise OcrEngineUnavailableError(
                f"Unable to run local Tesseract OCR: {str(exc)}",
                reason_code="ocr_execution_failed",
            )

        words: List[Dict[str, Any]] = []
        n_boxes = len(data.get("text", []))
        word_counter = 0

        for i in range(n_boxes):
            raw_txt = str(data["text"][i] or "").strip()
            if not raw_txt:
                continue
            try:
                conf_raw = float(data["conf"][i])
            except (ValueError, TypeError):
                conf_raw = -1.0
            if conf_raw < 0:
                continue

            word_counter += 1
            conf_norm = max(0.0, min(1.0, conf_raw / 100.0))
            left = int(data["left"][i])
            top = int(data["top"][i])
            width = int(data["width"][i])
            height = int(data["height"][i])
            block_num = data.get("block_num", [1] * n_boxes)[i]
            par_num = data.get("par_num", [1] * n_boxes)[i]
            line_num = data.get("line_num", [1] * n_boxes)[i]
            line_id = f"{block_num}_{par_num}_{line_num}"

            words.append({
                "word_id": f"p{page}_w{word_counter}",
                "text": raw_txt,
                "conf": round(conf_norm, 4),
                "bbox": [left, top, left + width, top + height],
                "page": page,
                "line_id": line_id,
                "script_guess": detect_script_guess(raw_txt),
            })

        return words


class VisionProvider:
    """
    Optional pluggable VisionProvider interface for low-trust / handwritten pages.
    Strictly OFF by default (`extraction.vision_provider.enabled = false`).
    Enabling requires:
      1. `extraction.vision_provider.enabled == True` in config, AND
      2. Explicit per-case officer consent in `case_settings` (`vision_cloud_consent == True`), AND
      3. Every invocation writes an entry to `audit_log` (without logging evidence content).
    """

    provider_name: str = "disabled_vision_provider"

    @staticmethod
    def is_enabled_in_config() -> bool:
        vp_cfg = get_extraction_config().get("vision_provider", {})
        return bool(vp_cfg.get("enabled", False))

    @staticmethod
    def has_case_consent(db: Session, case_id: str) -> bool:
        setting = db.query(CaseSetting).filter(CaseSetting.case_id == case_id).first()
        if not setting or not setting.settings_json:
            return False
        try:
            parsed = json.loads(setting.settings_json)
            return bool(parsed.get("vision_cloud_consent", False))
        except Exception:
            return False

    def recognize_with_consent(
        self,
        db: Session,
        case_id: str,
        evidence_id: str,
        page_no: int,
        user_id: str,
        image: Image.Image,
    ) -> Dict[str, Any]:
        vp_cfg = get_extraction_config().get("vision_provider", {})
        if not bool(vp_cfg.get("enabled", False)):
            raise PermissionError(
                "VisionProvider is disabled by configuration (air-gap default). Local OCR only."
            )
        if bool(vp_cfg.get("require_case_consent", True)) and not self.has_case_consent(db, case_id):
            raise PermissionError(
                f"VisionProvider requires explicit officer consent for case {case_id} before any external call."
            )

        # Log every invocation to cryptographic audit trail (never log evidence content)
        record_audit_log(
            db=db,
            user_id=user_id,
            action="VISION_PROVIDER_CALL",
            case_id=case_id,
            object_type="evidence_page",
            object_id=f"{evidence_id}:p{page_no}",
            details={
                "provider": self.provider_name,
                "evidence_id": evidence_id,
                "page_no": page_no,
                "source_kind": "vision_cloud",
            },
        )
        return self._invoke_backend(image=image, page_no=page_no)

    def _invoke_backend(self, image: Image.Image, page_no: int) -> Dict[str, Any]:
        """Hook for concrete vision backend when explicitly configured; default returns empty."""
        return {
            "words": [],
            "full_text": "",
            "mean_confidence": 0.0,
            "is_handwritten": True,
            "source_kind": "vision_cloud",
            "engine_name": self.provider_name,
            "engine_version": "1.0",
        }


_OCR_PROVIDER_OVERRIDE: Optional[OcrProvider] = None


def set_ocr_provider_override(provider: Optional[OcrProvider]) -> None:
    """Allows tests or alternative local OCR engines (e.g. PaddleOCR) to be injected cleanly."""
    global _OCR_PROVIDER_OVERRIDE
    _OCR_PROVIDER_OVERRIDE = provider


def get_ocr_provider() -> OcrProvider:
    """Returns the configured local OCR provider instance."""
    if _OCR_PROVIDER_OVERRIDE is not None:
        return _OCR_PROVIDER_OVERRIDE
    return TesseractProvider()


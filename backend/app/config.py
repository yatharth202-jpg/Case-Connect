import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "backend" / "config"
if not CONFIG_DIR.exists():
    CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

DEFAULTS_YAML_PATH = CONFIG_DIR / "defaults.yaml"
REFERENCE_DIR = CONFIG_DIR / "reference"
IFSC_BANK_CODES_PATH = REFERENCE_DIR / "ifsc_bank_codes.json"
FIR_PATTERNS_PATH = REFERENCE_DIR / "fir_patterns.yaml"
IPC_BNS_MAP_PATH = REFERENCE_DIR / "ipc_bns_map.json"

_DEFAULTS_CACHE: Optional[Dict[str, Any]] = None
_IFSC_BANK_CODES_CACHE: Optional[Dict[str, str]] = None
_IFSC_MISSING_WARNED: bool = False
_FIR_PATTERNS_CACHE: Optional[Dict[str, Any]] = None
_IPC_BNS_MAP_CACHE: Optional[Dict[str, Any]] = None


class Settings(BaseSettings):
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    DEBUG: bool = False

    # Databases
    DATABASE_URL: str = "sqlite:///./app.db"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "caseconnect2026"

    # Security
    JWT_SECRET: str = "supersecret-case-connect-jwt-key-2026-sih"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 8

    # File storage
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")

    # AI Engine (Google Gemini)
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Optional OCR / Media binary paths
    TESSERACT_CMD: str | None = None
    FFMPEG_CMD: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

# Ensure uploads directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


def get_defaults(force_reload: bool = False) -> Dict[str, Any]:
    """Loads global algorithmic and extraction defaults from backend/config/defaults.yaml."""
    global _DEFAULTS_CACHE
    if _DEFAULTS_CACHE is not None and not force_reload:
        return _DEFAULTS_CACHE
    if DEFAULTS_YAML_PATH.exists():
        try:
            with open(DEFAULTS_YAML_PATH, "r", encoding="utf-8") as f:
                _DEFAULTS_CACHE = yaml.safe_load(f) or {}
                return _DEFAULTS_CACHE
        except Exception as exc:
            logger.warning("Failed to load defaults.yaml (%s): %s", DEFAULTS_YAML_PATH, exc)
    _DEFAULTS_CACHE = {}
    return _DEFAULTS_CACHE


def get_extraction_config(force_reload: bool = False) -> Dict[str, Any]:
    """Returns the 'extraction' section from backend/config/defaults.yaml."""
    return get_defaults(force_reload=force_reload).get("extraction", {}) or {}


def get_merge_config(force_reload: bool = False) -> Dict[str, Any]:
    """Returns the 'merge' section from backend/config/defaults.yaml."""
    return get_defaults(force_reload=force_reload).get("merge", {}) or {}


def get_ifsc_bank_codes(force_reload: bool = False, custom_path: Optional[Path] = None) -> Dict[str, str]:
    """
    Loads 4-letter IFSC bank code prefix mappings from backend/config/reference/ifsc_bank_codes.json.
    If missing, logs a warning once and returns an empty dict so IFSC validation uses format-only mode.
    """
    global _IFSC_BANK_CODES_CACHE, _IFSC_MISSING_WARNED
    target_path = custom_path or IFSC_BANK_CODES_PATH
    if custom_path is None and _IFSC_BANK_CODES_CACHE is not None and not force_reload:
        return _IFSC_BANK_CODES_CACHE

    if target_path.exists():
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
                codes = {
                    str(k).upper(): str(v)
                    for k, v in raw.items()
                    if isinstance(k, str) and not k.startswith("_") and len(k) == 4
                }
                if custom_path is None:
                    _IFSC_BANK_CODES_CACHE = codes
                return codes
        except Exception as exc:
            logger.warning("Failed to read IFSC bank codes from %s: %s", target_path, exc)
            return {}
    else:
        if not _IFSC_MISSING_WARNED or custom_path is not None:
            logger.warning(
                "IFSC reference file missing at %s — falling back to format-only IFSC validation.",
                target_path,
            )
            if custom_path is None:
                _IFSC_MISSING_WARNED = True
        if custom_path is None:
            _IFSC_BANK_CODES_CACHE = {}
        return {}


def get_fir_patterns(force_reload: bool = False, custom_path: Optional[Path] = None) -> Dict[str, Any]:
    """Loads FIR role, kinship, relation, and stopword patterns from backend/config/reference/fir_patterns.yaml."""
    global _FIR_PATTERNS_CACHE
    target_path = custom_path or FIR_PATTERNS_PATH
    if custom_path is None and _FIR_PATTERNS_CACHE is not None and not force_reload:
        return _FIR_PATTERNS_CACHE
    if target_path.exists():
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                if custom_path is None:
                    _FIR_PATTERNS_CACHE = data
                return data
        except Exception as exc:
            logger.warning("Failed to load fir_patterns.yaml (%s): %s", target_path, exc)
    if custom_path is None:
        _FIR_PATTERNS_CACHE = {}
    return {}


def get_ipc_bns_map(force_reload: bool = False, custom_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Loads IPC <-> BNS / CrPC <-> BNSS / IT Act section mappings from
    backend/config/reference/ipc_bns_map.json.
    """
    global _IPC_BNS_MAP_CACHE
    target_path = custom_path or IPC_BNS_MAP_PATH
    if custom_path is None and _IPC_BNS_MAP_CACHE is not None and not force_reload:
        return _IPC_BNS_MAP_CACHE
    if target_path.exists():
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
                if custom_path is None:
                    _IPC_BNS_MAP_CACHE = data
                return data
        except Exception as exc:
            logger.warning("Failed to load ipc_bns_map.json (%s): %s", target_path, exc)
    if custom_path is None:
        _IPC_BNS_MAP_CACHE = {}
    return {}


# Eagerly load defaults & reference files at startup
get_defaults()
get_ifsc_bank_codes()
get_fir_patterns()
get_ipc_bns_map()

_EXTRACTOR_VERSION_CACHE: Optional[str] = None


def get_extractor_version(force_reload: bool = False) -> str:
    """
    Computes a deterministic, single EXTRACTOR_VERSION string combining:
      - App version: v2.0.0
      - Deterministic config hash (SHA-256 of extraction & merge defaults)
      - Key library versions (fitz/PyMuPDF, phonenumbers, pydantic, sqlalchemy)
    Stored on every record, field claim, and ingest run for forensic provenance.
    """
    global _EXTRACTOR_VERSION_CACHE
    if _EXTRACTOR_VERSION_CACHE is not None and not force_reload:
        return _EXTRACTOR_VERSION_CACHE

    import hashlib
    defaults = get_defaults(force_reload=force_reload)
    cfg_subset = {
        "extraction": defaults.get("extraction", {}),
        "merge": defaults.get("merge", {}),
    }
    cfg_hash = hashlib.sha256(
        json.dumps(cfg_subset, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:8]

    # Inspect key forensic library versions
    lib_parts = []
    try:
        import fitz
        lib_parts.append(f"fitz.{fitz.__version__}")
    except Exception:
        pass

    try:
        import phonenumbers
        lib_parts.append(f"pn.{phonenumbers.__version__}")
    except Exception:
        pass

    try:
        import pydantic
        lib_parts.append(f"pyd.{pydantic.__version__}")
    except Exception:
        pass

    try:
        import sqlalchemy
        lib_parts.append(f"sa.{sqlalchemy.__version__}")
    except Exception:
        pass

    lib_str = ".".join(lib_parts) if lib_parts else "std"
    version_str = f"v2.0.0+cfg.{cfg_hash}.{lib_str}"
    _EXTRACTOR_VERSION_CACHE = version_str
    return version_str


def validate_system_config(defaults: Optional[Dict[str, Any]] = None) -> None:
    """
    Startup configuration validator.
    Fails fast with a descriptive error message if required keys or sections
    in backend/config/defaults.yaml are missing or malformed.
    """
    if defaults is None:
        defaults = get_defaults()

    if not isinstance(defaults, dict) or not defaults:
        raise ValueError("CONFIGURATION ERROR: defaults.yaml could not be loaded or is empty.")

    ext_cfg = defaults.get("extraction")
    if not isinstance(ext_cfg, dict):
        raise ValueError("CONFIGURATION ERROR: 'extraction' section missing or not a dictionary in defaults.yaml.")

    required_extraction_keys = [
        "default_region",
        "timezone_display",
        "date_parse",
        "amount",
        "validators",
        "ocr",
        "media",
        "masking",
    ]
    for k in required_extraction_keys:
        if k not in ext_cfg:
            raise ValueError(f"CONFIGURATION ERROR: Missing required configuration key 'extraction.{k}' in defaults.yaml.")

    merge_cfg = defaults.get("merge")
    if not isinstance(merge_cfg, dict):
        raise ValueError("CONFIGURATION ERROR: 'merge' section missing or not a dictionary in defaults.yaml.")

    required_merge_keys = [
        "natural_keys",
        "source_trust_order",
        "conflict_confidence_margin",
        "min_confidence_auto_accept",
        "needs_review_below",
    ]
    for k in required_merge_keys:
        if k not in merge_cfg:
            raise ValueError(f"CONFIGURATION ERROR: Missing required configuration key 'merge.{k}' in defaults.yaml.")




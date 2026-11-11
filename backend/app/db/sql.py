import uuid
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean,
    DateTime, Text, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from backend.app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

# 1. Users
class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="investigator", nullable=False) # admin, investigator, viewer
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# 2. Cases
class Case(Base):
    __tablename__ = "cases"
    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String, default="medium", nullable=False) # high, medium, low
    status = Column(String, default="active", nullable=False) # active, analysis, closed
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# 3. Case Members
class CaseMember(Base):
    __tablename__ = "case_members"
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, ForeignKey("cases.id"), index=True, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    role = Column(String, default="investigator", nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# 4. Case Settings
class CaseSetting(Base):
    __tablename__ = "case_settings"
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, unique=True, index=True, nullable=False)
    settings_json = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# 5. Evidence Files
class EvidenceFile(Base):
    __tablename__ = "evidence_files"
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, ForeignKey("cases.id"), index=True, nullable=False)
    original_name = Column(String, nullable=False)
    stored_path = Column(String, nullable=False)
    sha256 = Column(String, index=True, nullable=False)
    file_size = Column(Integer, nullable=False)
    detected_type = Column(String, nullable=True) # cdr, bank_transactions, bank_statement, etc.
    status = Column(String, default="uploaded", nullable=False) # uploaded, mapped, ingesting, ingested, failed, needs_better_image
    uploader_id = Column(String, ForeignKey("users.id"), nullable=False)
    perceptual_hash = Column(String, index=True, nullable=True)
    exif_json = Column(Text, default="{}", nullable=True)
    is_handwritten = Column(Boolean, default=False, nullable=False)
    quality_json = Column(Text, default="{}", nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# 6. Column Mappings
class ColumnMapping(Base):
    __tablename__ = "column_mappings"
    id = Column(String, primary_key=True, default=generate_uuid)
    evidence_id = Column(String, ForeignKey("evidence_files.id"), index=True, nullable=False)
    mapping_json = Column(Text, nullable=False)
    confirmed_by = Column(String, ForeignKey("users.id"), nullable=False)
    confirmed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# 7. Mapping Templates
class MappingTemplate(Base):
    __tablename__ = "mapping_templates"
    id = Column(String, primary_key=True, default=generate_uuid)
    header_signature = Column(String, unique=True, index=True, nullable=False)
    file_type = Column(String, nullable=False)
    mapping_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# 8. Jobs
class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, index=True, nullable=False)
    job_type = Column(String, nullable=False) # ingest, recompute, report
    status = Column(String, default="queued", nullable=False) # queued, running, done, failed
    progress = Column(Integer, default=0, nullable=False)
    steps_json = Column(Text, default="[]", nullable=False)
    error_message = Column(Text, nullable=True)
    reason_code = Column(String, nullable=True, default=None)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# 9. Call Records (CDR Staging)
class CallRecord(Base):
    __tablename__ = "call_records"
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, index=True, nullable=False)
    source_file = Column(String, nullable=False)
    source_ref = Column(String, nullable=False) # row index
    caller = Column(String, index=True, nullable=False)
    receiver = Column(String, index=True, nullable=False)
    call_date = Column(String, nullable=True)
    call_time = Column(String, nullable=True)
    datetime_iso = Column(String, index=True, nullable=True)
    tz_source = Column(String, default="assumed_local", nullable=True)
    duration_seconds = Column(Integer, default=0, nullable=False)
    call_type = Column(String, nullable=True)
    imei = Column(String, nullable=True)
    imsi = Column(String, nullable=True)
    cell_id = Column(String, nullable=True)
    raw_json = Column(Text, default="{}", nullable=True)
    is_active = Column(Boolean, default=True, index=True, nullable=False)
    fingerprint = Column(String, index=True, nullable=False)

# 10. Transactions (Bank Staging)
class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, index=True, nullable=False)
    source_file = Column(String, nullable=False)
    source_ref = Column(String, nullable=False)
    txn_id = Column(String, index=True, nullable=True)
    from_account = Column(String, index=True, nullable=False)
    to_account = Column(String, index=True, nullable=False)
    from_name = Column(String, nullable=True)
    to_name = Column(String, nullable=True)
    amount_paise = Column(Integer, index=True, nullable=False) # Stored in paise
    date_iso = Column(String, index=True, nullable=False)
    tz_source = Column(String, default="assumed_local", nullable=True)
    reference = Column(String, nullable=True)
    direction = Column(String, nullable=True)
    raw_json = Column(Text, default="{}", nullable=True)
    is_active = Column(Boolean, default=True, index=True, nullable=False)
    fingerprint = Column(String, index=True, nullable=False)

# 11. IP Events
class IPEvent(Base):
    __tablename__ = "ip_events"
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, index=True, nullable=False)
    source_file = Column(String, nullable=False)
    source_ref = Column(String, nullable=False)
    identifier = Column(String, index=True, nullable=False)
    ip_address = Column(String, index=True, nullable=False)
    datetime_iso = Column(String, index=True, nullable=False)
    tz_source = Column(String, default="assumed_local", nullable=True)
    raw_json = Column(Text, default="{}", nullable=True)
    is_active = Column(Boolean, default=True, index=True, nullable=False)

# 12. Rejected Rows (Data Quality Audit)
class RejectedRow(Base):
    __tablename__ = "rejected_rows"
    id = Column(String, primary_key=True, default=generate_uuid)
    evidence_id = Column(String, index=True, nullable=False)
    case_id = Column(String, index=True, nullable=False)
    row_number = Column(Integer, nullable=False)
    raw_data_json = Column(Text, nullable=False)
    reason = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# 13. Staged Entities (Identity Tables & Graph Source)
class Entity(Base):
    __tablename__ = "entities"
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, index=True, nullable=False)
    label = Column(String, index=True, nullable=False) # Person, Phone, BankAccount, etc.
    canonical_id = Column(String, index=True, nullable=False)
    display_name = Column(String, nullable=False)
    properties_json = Column(Text, default="{}", nullable=False)
    source_file = Column(String, nullable=False)
    source_ref = Column(String, nullable=False)
    method = Column(String, default="structured", nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    is_active = Column(Boolean, default=True, index=True, nullable=False)

# 14. Staged Entity Links
class EntityLink(Base):
    __tablename__ = "entity_links"
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, index=True, nullable=False)
    source_entity_id = Column(String, index=True, nullable=False)
    target_entity_id = Column(String, index=True, nullable=False)
    relationship_type = Column(String, index=True, nullable=False)
    properties_json = Column(Text, default="{}", nullable=False)
    source_file = Column(String, nullable=False)
    source_ref = Column(String, nullable=False)
    method = Column(String, default="structured", nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    approved_by = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, index=True, nullable=False)

# 15. Extracted Entities (NLP / Review Queue)
class ExtractedEntity(Base):
    __tablename__ = "extracted_entities"
    id = Column(String, primary_key=True, default=generate_uuid)
    evidence_id = Column(String, index=True, nullable=False)
    case_id = Column(String, index=True, nullable=False)
    entity_type = Column(String, index=True, nullable=False)
    raw_value = Column(String, nullable=False)
    normalized_value = Column(String, index=True, nullable=False)
    page_or_paragraph = Column(String, nullable=False)
    page_no = Column(Integer, nullable=True)
    bbox_json = Column(Text, nullable=True)
    source_kind = Column(String, default="text_layer_pdf", nullable=True)
    char_span_start = Column(Integer, nullable=True)
    char_span_end = Column(Integer, nullable=True)
    confidence = Column(Float, default=0.5, nullable=False)
    method = Column(String, default="regex", nullable=False)
    status = Column(String, default="pending_review", index=True, nullable=False)
    reviewed_by = Column(String, nullable=True)

# 16. Match Suggestions (Entity Deduplication)
class MatchSuggestion(Base):
    __tablename__ = "match_suggestions"
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, index=True, nullable=False)
    entity_a_id = Column(String, index=True, nullable=False)
    entity_b_id = Column(String, index=True, nullable=False)
    level = Column(String, index=True, nullable=False) # HIGH, MEDIUM, SHARED_DEVICE, LOW
    score = Column(Float, nullable=False)
    reasons_json = Column(Text, default="[]", nullable=False)
    status = Column(String, default="pending", index=True, nullable=False) # pending, approved, rejected, undone
    decided_by = Column(String, nullable=True)
    decided_at = Column(DateTime, nullable=True)

# 17. Master Profile Members
class ProfileMember(Base):
    __tablename__ = "profile_members"
    id = Column(String, primary_key=True, default=generate_uuid)
    profile_id = Column(String, index=True, nullable=False)
    entity_id = Column(String, index=True, nullable=False)
    match_id = Column(String, nullable=True)
    approved_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# 18. Lead Decisions
class LeadDecision(Base):
    __tablename__ = "lead_decisions"
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, index=True, nullable=False)
    lead_id = Column(String, index=True, nullable=False)
    decision = Column(String, nullable=False) # accept, reject, need_more_data
    notes = Column(Text, nullable=True)
    officer_id = Column(String, nullable=False)
    decided_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# 19. Anomaly Alerts
class Alert(Base):
    __tablename__ = "alerts"
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, index=True, nullable=False)
    entity_id = Column(String, index=True, nullable=False)
    pattern_type = Column(String, index=True, nullable=False)
    severity = Column(String, default="medium", nullable=False)
    alert_date = Column(String, nullable=False)
    explanation = Column(Text, nullable=False)
    evidence_ids_json = Column(Text, default="[]", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# 20. Investigation Reports
class Report(Base):
    __tablename__ = "reports"
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, index=True, nullable=False)
    report_title = Column(String, nullable=False)
    stored_path = Column(String, nullable=False)
    sha256 = Column(String, nullable=False)
    generated_by = Column(String, nullable=False)
    parameters_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# 21. Cryptographic Audit Log
class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(String, primary_key=True, default=generate_uuid)
    ts = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    action = Column(String, index=True, nullable=False)
    case_id = Column(String, index=True, nullable=True)
    object_type = Column(String, nullable=True)
    object_id = Column(String, nullable=True)
    details_json = Column(Text, default="{}", nullable=False)
    prev_hash = Column(String, nullable=False)
    hash = Column(String, index=True, nullable=False)

# 22. Saved Views
class SavedView(Base):
    __tablename__ = "saved_views"
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    view_config_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# 23. Unified Extraction Records (Extraction V2 Store)
class ExtractionRecord(Base):
    __tablename__ = "extraction_records"
    __table_args__ = (
        UniqueConstraint(
            "case_id", "record_type", "natural_key", "occurrence_idx", "evidence_id",
            name="uq_extraction_record_occurrence",
        ),
    )
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, ForeignKey("cases.id"), index=True, nullable=False)
    evidence_id = Column(String, index=True, nullable=False)
    record_type = Column(String, index=True, nullable=False) # transaction, call, ip_event, entity, document_fact
    natural_key = Column(String, index=True, nullable=False) # deterministic hash of natural key fields
    occurrence_idx = Column(Integer, default=1, nullable=False) # Nth identical key within the same evidence file
    data_json = Column(Text, default="{}", nullable=False) # known canonical fields
    extra_json = Column(Text, default="{}", nullable=False) # unknown/new fields, never dropped
    raw_json = Column(Text, default="{}", nullable=False) # original raw values
    source_ref = Column(String, nullable=True)
    page_no = Column(Integer, nullable=True)
    bbox_json = Column(Text, nullable=True)
    timestamp_sec = Column(Float, nullable=True)
    method = Column(String, default="structured", nullable=False)
    source_kind = Column(String, default="structured_file", nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    extractor_version = Column(String, default="2.0.0", nullable=False)
    status = Column(String, default="active", index=True, nullable=False) # active | merged | retracted | rejected
    merged_into_id = Column(String, index=True, nullable=True)
    staged_table = Column(String, nullable=True)
    staged_id = Column(String, index=True, nullable=True)
    first_seen_run_id = Column(String, nullable=True)
    last_seen_run_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# 24. Record Sources (Multi-File Confirmation Provenance)
class RecordSource(Base):
    __tablename__ = "record_sources"
    id = Column(String, primary_key=True, default=generate_uuid)
    record_id = Column(String, ForeignKey("extraction_records.id"), index=True, nullable=False)
    evidence_id = Column(String, index=True, nullable=False)
    source_ref = Column(String, nullable=True)
    seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# 25. Field Claims (Per-Field Evidence Claims)
class FieldClaim(Base):
    __tablename__ = "field_claims"
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, index=True, nullable=False)
    subject_type = Column(String, index=True, nullable=False) # entity | record
    subject_id = Column(String, index=True, nullable=False)
    field_name = Column(String, index=True, nullable=False)
    value_norm = Column(Text, nullable=True)
    value_raw = Column(Text, nullable=True)
    evidence_id = Column(String, index=True, nullable=False)
    source_ref = Column(String, nullable=True)
    source_kind = Column(String, default="structured_file", nullable=False)
    method = Column(String, default="structured", nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    validator_ok = Column(Boolean, default=True, nullable=False)
    status = Column(String, default="active", index=True, nullable=False) # active | retracted
    observed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    run_id = Column(String, index=True, nullable=True)

# 26. Golden Fields (Resolved Winner Per Subject & Field)
class GoldenField(Base):
    __tablename__ = "golden_fields"
    __table_args__ = (
        UniqueConstraint("subject_type", "subject_id", "field_name", name="uq_golden_field_subject"),
    )
    id = Column(String, primary_key=True, default=generate_uuid)
    subject_type = Column(String, index=True, nullable=False) # entity | record
    subject_id = Column(String, index=True, nullable=False)
    field_name = Column(String, index=True, nullable=False)
    selected_claim_id = Column(String, index=True, nullable=True)
    selected_by = Column(String, default="auto", nullable=False) # auto | officer
    locked = Column(Boolean, default=False, nullable=False)
    reason_code = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# 27. Merge Conflicts (Unresolved Competing Claims)
class MergeConflict(Base):
    __tablename__ = "merge_conflicts"
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, index=True, nullable=False)
    subject_type = Column(String, index=True, nullable=False) # entity | record
    subject_id = Column(String, index=True, nullable=False)
    field_name = Column(String, index=True, nullable=False)
    claim_ids_json = Column(Text, default="[]", nullable=False)
    status = Column(String, default="open", index=True, nullable=False) # open | resolved | dismissed
    resolution_claim_id = Column(String, nullable=True)
    resolved_by = Column(String, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    reason_code = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# 28. Ingest Runs (Merge Changelog & Preview/Apply/Rollback Audit)
class IngestRun(Base):
    __tablename__ = "ingest_runs"
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, index=True, nullable=False)
    evidence_id = Column(String, index=True, nullable=False)
    job_id = Column(String, nullable=True)
    mode = Column(String, nullable=False) # preview | apply | rollback
    counts_json = Column(Text, default="{}", nullable=False) # new, same, updated, new_fields, conflicts, rejected
    status = Column(String, default="done", nullable=False)
    extractor_version = Column(String, default="2.0.0", nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)

# 29. Dynamic Schema Registry (Unknown/Extra Field Discovery)
class SchemaRegistry(Base):
    __tablename__ = "schema_registry"
    __table_args__ = (
        UniqueConstraint("record_type", "field_name", name="uq_schema_registry_type_field"),
    )
    id = Column(String, primary_key=True, default=generate_uuid)
    record_type = Column(String, index=True, nullable=False)
    field_name = Column(String, index=True, nullable=False)
    seen_count = Column(Integer, default=1, nullable=False)
    first_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    promoted = Column(Boolean, default=False, nullable=False)

# 30. Officer Annotations & Tags (Append-Only with Soft Delete)
class Annotation(Base):
    __tablename__ = "annotations"
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, ForeignKey("cases.id"), index=True, nullable=False)
    subject_type = Column(String, index=True, nullable=False) # record | entity
    subject_id = Column(String, index=True, nullable=False)
    note_text = Column(Text, nullable=True)
    tags_json = Column(Text, default="[]", nullable=False)
    created_by = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_deleted = Column(Boolean, default=False, index=True, nullable=False)
    deleted_by = Column(String, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

# 31. Evidence Document/OCR Pages (Per-Page Provenance, Quality Gate & Word Boxes)
class EvidencePage(Base):
    __tablename__ = "evidence_pages"
    __table_args__ = (
        UniqueConstraint("evidence_id", "page_no", name="uq_evidence_page_no"),
    )
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, ForeignKey("cases.id"), index=True, nullable=False)
    evidence_id = Column(String, ForeignKey("evidence_files.id"), index=True, nullable=False)
    page_no = Column(Integer, nullable=False)
    source_kind = Column(String, default="text_layer_pdf", nullable=False) # text_layer_pdf | ocr_printed | ocr_handwritten
    status = Column(String, default="ready", index=True, nullable=False) # ready | needs_better_image | pending_review | ocr_unavailable
    quality_reason = Column(Text, nullable=True)
    quality_metrics_json = Column(Text, default="{}", nullable=False)
    preprocess_params_json = Column(Text, default="{}", nullable=False)
    raw_text = Column(Text, default="", nullable=False) # Original OCR/text-layer text (never overwritten)
    corrected_text = Column(Text, nullable=True) # Reconstructed text after officer corrections
    words_json = Column(Text, default="[]", nullable=False) # List of {word_id, text, conf, bbox, page, line_id, script_guess, ...}
    page_image_sha256 = Column(String, nullable=True)
    perceptual_hash = Column(String, index=True, nullable=True)
    exif_json = Column(Text, default="{}", nullable=False)
    engine_name = Column(String, default="pymupdf", nullable=False)
    engine_version = Column(String, default="1.0", nullable=False)
    mean_confidence = Column(Float, default=1.0, nullable=False)
    is_handwritten = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

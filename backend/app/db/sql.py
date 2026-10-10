import uuid
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean,
    DateTime, Text, ForeignKey, Index
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
    status = Column(String, default="uploaded", nullable=False) # uploaded, mapped, ingesting, ingested, failed
    uploader_id = Column(String, ForeignKey("users.id"), nullable=False)
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
    duration_seconds = Column(Integer, default=0, nullable=False)
    call_type = Column(String, nullable=True)
    imei = Column(String, nullable=True)
    imsi = Column(String, nullable=True)
    cell_id = Column(String, nullable=True)
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
    reference = Column(String, nullable=True)
    direction = Column(String, nullable=True)
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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

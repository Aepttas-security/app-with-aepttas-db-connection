# caller_backend/models.py
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, BigInteger,
    ForeignKey, Float, Text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from database import Base

class MetadataBase:
    created_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    created_date = Column(DateTime, server_default=func.now(), nullable=False)
    last_updated_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_updated_date = Column(DateTime, server_default=func.now(), nullable=False)
    last_dml_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_dml_date = Column(DateTime, server_default=func.now(), nullable=False)
    last_ddl_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_ddl_date = Column(DateTime, server_default=func.now(), nullable=False)
    program_id = Column(BigInteger, default=1)

# ==========================================================
# 👤 CORE USERS
# ==========================================================
class AptUsersB(Base, MetadataBase):
    __tablename__ = 'apt_users_b'
    __table_args__ = {'schema': 'apt', 'extend_existing': True}
    user_id = Column(BigInteger, primary_key=True, index=True)
    user_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    username = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)

# ==========================================================
# 📞 CALLER INTELLIGENCE
# ==========================================================
class AptCallersB(Base, MetadataBase):
    __tablename__ = 'apt_callers_b'
    __table_args__ = {'schema': 'apt', 'extend_existing': True}
    caller_id = Column(BigInteger, primary_key=True, index=True)
    caller_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    phone_number = Column(String(20), nullable=False, unique=True)
    caller_name = Column(String(200))
    is_spam_reported = Column(Boolean, default=False, nullable=False)
    risk_level_id = Column(BigInteger, default=1)

class AptCallsB(Base, MetadataBase):
    __tablename__ = 'apt_calls_b'
    __table_args__ = {'schema': 'apt', 'extend_existing': True}
    call_id = Column(BigInteger, primary_key=True, index=True)
    call_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    user_id = Column(BigInteger, nullable=False, default=1)
    caller_id = Column(BigInteger, nullable=False)
    phone_number = Column(String(20), nullable=False)
    call_type = Column(String(20), nullable=False)
    call_duration_seconds = Column(Integer, default=0, nullable=False)
    call_timestamp = Column(DateTime, nullable=False, default=func.now())
    status_id = Column(BigInteger, default=1)

class AptBlockedNumbersB(Base, MetadataBase):
    __tablename__ = 'apt_blocked_numbers_b'
    __table_args__ = {'schema': 'apt', 'extend_existing': True}
    blocked_number_id = Column(BigInteger, primary_key=True, index=True)
    blocked_number_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    user_id = Column(BigInteger, nullable=False, default=1)
    caller_id = Column(BigInteger)
    phone_number = Column(String(20), nullable=False)
    blocked_date = Column(DateTime, server_default=func.now(), nullable=False)
    reason = Column(String(500))

class AptReportsB(Base, MetadataBase):
    __tablename__ = 'apt_reports_b'
    __table_args__ = {'schema': 'apt', 'extend_existing': True}
    report_id = Column(BigInteger, primary_key=True, index=True)
    report_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    user_id = Column(BigInteger, nullable=False, default=1)
    caller_id = Column(BigInteger)
    call_id = Column(BigInteger)
    phone_number = Column(String(20), nullable=False)
    report_reason = Column(String(500), nullable=False)
    status_id = Column(BigInteger, default=1)

class AptAlertsB(Base, MetadataBase):
    __tablename__ = 'apt_alerts_b'
    __table_args__ = {'schema': 'apt', 'extend_existing': True}
    alert_id = Column(BigInteger, primary_key=True, index=True)
    alert_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    user_id = Column(BigInteger, nullable=False, default=1)
    caller_id = Column(BigInteger)
    call_id = Column(BigInteger)
    phone_number = Column(String(20))
    severity_id = Column(BigInteger, nullable=False, default=1)
    alert_message = Column(String(1000), nullable=False)
    is_acknowledged = Column(Boolean, default=False, nullable=False)

class AptCallSettingsB(Base, MetadataBase):
    __tablename__ = 'apt_call_settings_b'
    __table_args__ = {'schema': 'apt', 'extend_existing': True}
    call_setting_id = Column(BigInteger, primary_key=True, index=True)
    call_setting_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    user_id = Column(BigInteger, nullable=False, default=1)
    auto_block_spam = Column(Boolean, default=True, nullable=False)
    block_unknown_numbers = Column(Boolean, default=False, nullable=False)
    notification_type_id = Column(BigInteger, default=1)

# ==========================================================
# 📍 GEOLOCATION
# ==========================================================
class GeolocationScan(Base):
    __tablename__ = "apt_location_records_b"
    __table_args__ = {'schema': 'apt', 'extend_existing': True}
    location_record_id = Column(BigInteger, primary_key=True, index=True)
    location_record_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    device_id = Column(String(128), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float, default=0.0)
    speed_kmh = Column(Float, default=0.0)
    provider = Column(String(32), default="gps")
    platform = Column(String(16), default="android")
    app_version = Column(String(32), default="1.0.0")
    city = Column(String(128))
    country = Column(String(128))
    address = Column(Text)
    gps_timestamp = Column(DateTime, nullable=False, default=func.now())
    is_spoofed = Column(Boolean, default=False)
    spoof_confidence = Column(String(32), default="low")
    spoof_reasons = Column(JSONB, default=list)
    raw_provider_flags = Column(JSONB, default=dict)
    user_id = Column(BigInteger, default=1)
    program_id = Column(BigInteger, default=1)
    is_active = Column(Boolean, default=True)
    attributes = Column(JSONB, default=dict)
    created_by = Column(String(100), default="system")
    created_at = Column(DateTime, default=func.now())

class NearbyPlace(Base):
    __tablename__ = "apt_nearby_places_b"
    __table_args__ = {'schema': 'apt', 'extend_existing': True}
    nearby_place_id = Column(BigInteger, primary_key=True, index=True)
    nearby_place_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    place_name = Column(String(255), nullable=False)
    place_type = Column(String(32), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(Text)
    city = Column(String(128))
    country = Column(String(128))
    is_active = Column(Boolean, default=True)
    attributes = Column(JSONB, default=dict)
    program_id = Column(BigInteger, default=1)

# ==========================================================
# 🛡️ MALWARE SCANNING
# ==========================================================
class ScanRecord(Base):
    __tablename__ = 'apt_scans_b'
    __table_args__ = {'schema': 'apt', 'extend_existing': True}
    id = Column(BigInteger, primary_key=True, index=True)
    scan_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    filename = Column(String(255), nullable=False)
    package_name = Column(String(255))
    version = Column(String(50), default="1.0.0")
    file_path = Column(String(500))
    risk_score = Column(Integer, default=0)
    risk_level = Column(String(50), default="SAFE")
    threat_type = Column(String(100), default="None")
    permissions = Column(Text)
    confidence_score = Column(Float, default=0.95)
    recommended_action = Column(String(100), default="KEEP")
    status = Column(String(50), default="CLEAN")
    timestamp = Column(BigInteger)

class QuarantineRecord(Base):
    __tablename__ = 'apt_quarantine_b'
    __table_args__ = {'schema': 'apt', 'extend_existing': True}
    id = Column(BigInteger, primary_key=True, index=True)
    scan_id = Column(BigInteger)
    filename = Column(String(255), nullable=False)
    package_name = Column(String(255))
    original_path = Column(String(500))
    quarantine_path = Column(String(500))
    threat_summary = Column(Text)
    timestamp = Column(BigInteger)

# ==========================================================
# 🔍 VULNERABILITY & APP RISKS
# ==========================================================
class PermissionScan(Base):
    __tablename__ = 'apt_permission_scans_b'
    __table_args__ = {'schema': 'apt', 'extend_existing': True}
    permission_scan_id = Column(BigInteger, primary_key=True, index=True)
    permission_scan_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    package_name = Column(String(255), nullable=False)
    app_name = Column(String(255))
    category = Column(String(100))
    requested_permissions = Column(JSONB, default=list)
    flagged_permissions = Column(JSONB, default=list)
    risk = Column(String(50), default="safe")
    reason = Column(Text)
    is_outdated = Column(Boolean, default=False)
    play_store_url = Column(String(500))
    user_id = Column(BigInteger, default=1)
    scan_scenario = Column(String(10), default="B")
    is_active = Column(Boolean, default=True)
    scanned_at = Column(DateTime, default=func.now())

class RiskReport(Base):
    __tablename__ = 'apt_app_risk_reports_b'
    __table_args__ = {'schema': 'apt', 'extend_existing': True}
    risk_report_id = Column(BigInteger, primary_key=True, index=True)
    risk_report_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    package_name = Column(String(255), nullable=False)
    risk = Column(String(50), default="Low")
    storage_status = Column(String(50), default="secure")
    storage_detail = Column(Text)
    code_status = Column(String(50), default="secure")
    code_detail = Column(Text)
    ipc_status = Column(String(50), default="secure")
    ipc_detail = Column(Text)
    user_id = Column(BigInteger, default=1)
    permission_scan_id = Column(BigInteger)
    scan_scenario = Column(String(10), default="A")
    is_active = Column(Boolean, default=True)
    scanned_at = Column(DateTime, default=func.now())
    attributes = Column(JSONB, default=dict)

class OutdatedApp(Base):
    __tablename__ = 'apt_outdated_apps_b'
    __table_args__ = {'schema': 'apt', 'extend_existing': True}
    id = Column(BigInteger, primary_key=True, index=True)
    package_name = Column(String(255), nullable=False)
    app_name = Column(String(255))
    current_version = Column(String(50))
    latest_version = Column(String(50))
    user_id = Column(BigInteger, default=1)
    is_active = Column(Boolean, default=True)
    detected_at = Column(DateTime, default=func.now())

# ==========================================================
# 👨‍👩‍👧 PARENTAL CONTROL
# ==========================================================
class Child(Base):
    __tablename__ = 'apt_children_b'
    __table_args__ = {'schema': 'apt', 'extend_existing': True}
    child_id = Column(String(100), primary_key=True, index=True)
    parent_id = Column(BigInteger, default=1)
    name = Column(String(100), nullable=False)
    age = Column(Integer, default=10)
    device = Column(String(100), default="Android Device")
    battery = Column(String(20), default="85%")
    is_active_online = Column(Boolean, default=True)
    linking_code = Column(String(20))
    created_at = Column(DateTime, default=func.now())

class ScreenTime(Base):
    __tablename__ = 'apt_screentime_b'
    __table_args__ = {'schema': 'apt', 'extend_existing': True}
    id = Column(BigInteger, primary_key=True, index=True)
    child_id = Column(String(100), nullable=False, index=True)
    daily_limit_minutes = Column(Integer, default=120)
    current_usage_minutes = Column(Integer, default=45)
    is_locked_remotely = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=func.now())

class AppRestriction(Base):
    __tablename__ = 'apt_app_restrictions_b'
    __table_args__ = {'schema': 'apt', 'extend_existing': True}
    id = Column(BigInteger, primary_key=True, index=True)
    child_id = Column(String(100), nullable=False, index=True)
    app_id = Column(String(100), nullable=False)
    app_name = Column(String(150), nullable=False)
    category = Column(String(50), default="Games")
    is_blocked = Column(Boolean, default=False)

class FilterRule(Base):
    __tablename__ = 'apt_filter_rules_b'
    __table_args__ = {'schema': 'apt', 'extend_existing': True}
    id = Column(BigInteger, primary_key=True, index=True)
    child_id = Column(String(100), nullable=False, index=True)
    category = Column(String(100), nullable=False)
    is_blocked = Column(Boolean, default=False)

class BlacklistedUrl(Base):
    __tablename__ = 'apt_blacklisted_urls_b'
    __table_args__ = {'schema': 'apt', 'extend_existing': True}
    id = Column(BigInteger, primary_key=True, index=True)
    child_id = Column(String(100), nullable=False, index=True)
    url = Column(String(500), nullable=False)

class SosAlert(Base):
    __tablename__ = 'apt_sos_alerts_b'
    __table_args__ = {'schema': 'apt', 'extend_existing': True}
    id = Column(BigInteger, primary_key=True, index=True)
    child_id = Column(String(100), nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    latitude = Column(Float)
    longitude = Column(Float)
    alert_message = Column(String(255), default="Emergency SOS triggered")
    created_at = Column(DateTime, default=func.now())

class PairingCode(Base):
    __tablename__ = 'apt_pairing_codes_b'
    __table_args__ = {'schema': 'apt', 'extend_existing': True}
    id = Column(BigInteger, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)
    parent_id = Column(BigInteger, default=1)
    child_id = Column(String(100))
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

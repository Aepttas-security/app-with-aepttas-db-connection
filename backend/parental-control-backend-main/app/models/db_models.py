import uuid
from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    String,
    Boolean,
    Numeric,
    ForeignKey,
    DateTime,
    Text,
    Date,
    UniqueConstraint,  # Added to resolve NameError
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
# ==========================================
# 1. USERS MODEL (MATCHES apt.apt_users_b)
# ==========================================
class User(Base):
    __tablename__ = "apt_users_b"
    
    id = Column("user_id", Integer, primary_key=True, autoincrement=True)
    user_uuid = Column("user_uuid", UUID(as_uuid=True), default=uuid.uuid4)
    name = Column("username", String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_email_verified = Column(Boolean, default=True)
    is_phone_verified = Column(Boolean, default=False)
    created_by = Column(String(255), default="SYSTEM")
    created_date = Column(DateTime, server_default=func.now())
    last_updated_by = Column(String(255), default="SYSTEM")
    last_updated_date = Column(DateTime, server_default=func.now())
    last_dml_by = Column(String(255), default="SYSTEM")
    last_dml_date = Column(DateTime, server_default=func.now())
    last_ddl_by = Column(String(255), default="SYSTEM")
    last_ddl_date = Column(DateTime, server_default=func.now())

# ==========================================
# 2. CHILDREN MODEL (MATCHES apt.apt_children_b)
# ==========================================
class Child(Base):
    __tablename__ = "apt_children_b"
    
    child_id = Column("child_id", Integer, primary_key=True, autoincrement=True)
    child_uuid = Column("child_uuid", UUID(as_uuid=True), default=uuid.uuid4)
    parent_id = Column("parent_user_id", Integer, ForeignKey("apt_users_b.user_id", ondelete="CASCADE"), nullable=False)
    child_name = Column(String(200), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    age = Column(Integer, nullable=True)
    linking_code = Column(String(10), unique=True, nullable=True)
    created_by = Column(String(255), default="SYSTEM")
    created_date = Column(DateTime, server_default=func.now())
    last_updated_by = Column(String(255), default="SYSTEM")
    last_updated_date = Column(DateTime, server_default=func.now())
    last_dml_by = Column(String(255), default="SYSTEM")
    last_dml_date = Column(DateTime, server_default=func.now())
    last_ddl_by = Column(String(255), default="SYSTEM")
    last_ddl_date = Column(DateTime, server_default=func.now())

# ==========================================
# 3. SOS ALERTS MODEL (MATCHES apt.apt_sos_alerts_b)
# ==========================================
class SOSAlertTable(Base):
    __tablename__ = "apt_sos_alerts_b"
    
    id = Column("sos_alert_id", Integer, primary_key=True, autoincrement=True)
    sos_alert_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4)
    child_id = Column("child_id", Integer, nullable=True)
    child_uuid = Column(UUID(as_uuid=True), nullable=True)
    latitude = Column(Numeric(10, 7), nullable=False)
    longitude = Column(Numeric(10, 7), nullable=False)
    current_address = Column(Text, nullable=True)
    timestamp = Column("triggered_date", DateTime, server_default=func.now(), nullable=False)
    is_resolved = Column(Boolean, default=False, nullable=False)
    created_by = Column(String(255), default="SYSTEM")
    created_date = Column(DateTime, server_default=func.now())
    last_updated_by = Column(String(255), default="SYSTEM")
    last_updated_date = Column(DateTime, server_default=func.now())
    last_dml_by = Column(String(255), default="SYSTEM")
    last_dml_date = Column(DateTime, server_default=func.now())
    last_ddl_by = Column(String(255), default="SYSTEM")
    last_ddl_date = Column(DateTime, server_default=func.now())

# ===================================================================================
# 4. LOCATION MODEL (MATCHES apt.apt_child_location_b)
# ===================================================================================
class LocationTable(Base):
    __tablename__ = "apt_child_location_b"
    
    child_location_id = Column(Integer, primary_key=True, autoincrement=True)
    child_location_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4)
    child_id = Column(Integer, nullable=False, index=True)
    pairing_id = Column(Integer, nullable=True)
    latitude = Column(Numeric(10, 7), nullable=False)
    longitude = Column(Numeric(10, 7), nullable=False)
    current_address = Column(Text, nullable=True)
    battery_percentage = Column(Integer, nullable=True)
    is_tracking_enabled = Column(Boolean, default=True, nullable=False)
    is_geofence_enabled = Column(Boolean, default=True, nullable=False)
    last_updated = Column("recorded_date", DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(255), default="SYSTEM")
    created_date = Column(DateTime, server_default=func.now())
    last_updated_by = Column(String(255), default="SYSTEM")
    last_updated_date = Column(DateTime, server_default=func.now())
    last_dml_by = Column(String(255), default="SYSTEM")
    last_dml_date = Column(DateTime, server_default=func.now())
    last_ddl_by = Column(String(255), default="SYSTEM")
    last_ddl_date = Column(DateTime, server_default=func.now())

# ===================================================================================
# 5. SCREENTIME SETTINGS MODEL (MATCHES apt.apt_screen_time_b)
# ===================================================================================
from datetime import date

class ScreentimeSettingsTable(Base):
    __tablename__ = "apt_screen_time_b"
    
    screen_time_id = Column(Integer, primary_key=True, autoincrement=True)
    screen_time_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4)
    child_id = Column(Integer, nullable=False, index=True)
    daily_limit_minutes = Column(Integer, default=240, nullable=False)
    record_date = Column(Date, default=date.today, nullable=False)
    minutes_used = Column(Integer, default=0, nullable=False)
    created_by = Column(String(255), default="SYSTEM")
    created_date = Column(DateTime, server_default=func.now())
    last_updated_by = Column(String(255), default="SYSTEM")
    last_updated_date = Column(DateTime, server_default=func.now())
    last_dml_by = Column(String(255), default="SYSTEM")
    last_dml_date = Column(DateTime, server_default=func.now())
    last_ddl_by = Column(String(255), default="SYSTEM")
    last_ddl_date = Column(DateTime, server_default=func.now())

    @property
    def current_usage_minutes(self):
        return self.minutes_used or 0

    @current_usage_minutes.setter
    def current_usage_minutes(self, val):
        self.minutes_used = val

    @property
    def is_locked_remotely(self):
        return getattr(self, "_is_locked_remotely", False)

    @is_locked_remotely.setter
    def is_locked_remotely(self, val):
        self._is_locked_remotely = val


# =================================================================================
# 6. GEOFENCE ZONE MODEL (MATCHES apt.apt_geofence_b)
# =================================================================================
class GeofenceZoneTable(Base):
    __tablename__ = "apt_geofence_b"
    
    geofence_id = Column(Integer, primary_key=True, autoincrement=True)
    geofence_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4)
    child_id = Column(Integer, nullable=False, index=True)
    zone_name = Column("fence_name", String(200), nullable=False)
    latitude = Column("center_latitude", Numeric(10, 7), nullable=False)
    longitude = Column("center_longitude", Numeric(10, 7), nullable=False)
    radius_meters = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column("created_date", DateTime, server_default=func.now())
    created_by = Column(String(255), default="SYSTEM")
    last_updated_by = Column(String(255), default="SYSTEM")
    last_updated_date = Column(DateTime, server_default=func.now())
    last_dml_by = Column(String(255), default="SYSTEM")
    last_dml_date = Column(DateTime, server_default=func.now())
    last_ddl_by = Column(String(255), default="SYSTEM")
    last_ddl_date = Column(DateTime, server_default=func.now())

# ================================================================================
# 7. FILTER POLICY MODEL (MATCHES apt.apt_filter_policy_b)
# ================================================================================
class FilterPolicyTable(Base):
    __tablename__ = "apt_filter_policy_b"
    
    id = Column("filter_policy_id", Integer, primary_key=True, autoincrement=True)
    filter_policy_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4)
    child_id = Column(Integer, nullable=False, index=True)
    category_key = Column("category", String(100), nullable=False)
    is_enabled = Column("is_blocked", Boolean, default=True, nullable=False)
    created_at = Column("created_date", DateTime, server_default=func.now())
    created_by = Column(String(255), default="SYSTEM")
    last_updated_by = Column(String(255), default="SYSTEM")
    last_updated_date = Column(DateTime, server_default=func.now())
    last_dml_by = Column(String(255), default="SYSTEM")
    last_dml_date = Column(DateTime, server_default=func.now())
    last_ddl_by = Column(String(255), default="SYSTEM")
    last_ddl_date = Column(DateTime, server_default=func.now())

# ================================================================================
# 8. DEVICE PAIRING MODEL (MATCHES apt.apt_device_pairing_b)
# ================================================================================
class DevicePairingTable(Base):
    __tablename__ = "apt_device_pairing_b"
    
    pairing_id = Column(Integer, primary_key=True, autoincrement=True)
    pairing_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4)
    child_id = Column(Integer, nullable=True)
    device_identifier = Column(String(255), nullable=True)
    device_name = Column(String(255), nullable=True)
    paired_date = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)
    linking_code = Column(String(10), nullable=True)
    parent_id = Column(Integer, nullable=True)
    child_uuid = Column(UUID(as_uuid=True), nullable=True)
    status = Column(String(20), default="PENDING")
    child_consent_given = Column(Boolean, default=False)
    created_by = Column(String(255), default="SYSTEM")
    created_date = Column(DateTime, server_default=func.now())
    last_updated_by = Column(String(255), default="SYSTEM")
    last_updated_date = Column(DateTime, server_default=func.now())
    last_dml_by = Column(String(255), default="SYSTEM")
    last_dml_date = Column(DateTime, server_default=func.now())
    last_ddl_by = Column(String(255), default="SYSTEM")
    last_ddl_date = Column(DateTime, server_default=func.now())

# ================================================================================
# 9. CALLER INTEL BLOCKED NUMBERS MODEL
# ================================================================================
class CallerIntelBlockedTable(Base):
    __tablename__ = "apt_caller_intel_blocked_b"

    id = Column(Integer, primary_key=True, autoincrement=True)
    child_id = Column(Integer, nullable=True, default=1)
    phone_number = Column(String(50), nullable=False)
    caller_name = Column(String(200), nullable=True)
    block_reason = Column(String(255), nullable=True)
    date_added = Column(String(50), nullable=True)

# ================================================================================
# 10. CALLER INTEL REPORTS MODEL
# ================================================================================
class CallerIntelReportTable(Base):
    __tablename__ = "apt_caller_intel_reports_b"

    id = Column(Integer, primary_key=True, autoincrement=True)
    child_id = Column(Integer, nullable=True, default=1)
    phone_number = Column(String(50), nullable=False)
    report_type = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    timestamp = Column(String(100), nullable=True)

# ================================================================================
# 11. CALLER INTEL SETTINGS MODEL
# ================================================================================
class CallerIntelSettingsTable(Base):
    __tablename__ = "apt_caller_intel_settings_b"

    id = Column(Integer, primary_key=True, autoincrement=True)
    child_id = Column(Integer, unique=True, default=1)
    auto_block_enabled = Column(Boolean, default=True)
    notifications_enabled = Column(Boolean, default=True)

# ================================================================================
# 12. BLACKLISTED URLS MODEL
# ================================================================================
class BlacklistedUrlTable(Base):
    __tablename__ = "apt_blacklisted_urls_b"

    id = Column(Integer, primary_key=True, autoincrement=True)
    child_id = Column(Integer, nullable=False, default=1, index=True)
    url = Column(String(500), nullable=False)
    added_date = Column(DateTime, server_default=func.now())

# ================================================================================
# 13. SCANS MODEL
# ================================================================================
class ScanTable(Base):
    __tablename__ = "apt_scans_b"

    scan_id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(255), nullable=False)
    package_name = Column(String(255), nullable=True)
    threat_level = Column(String(50), default="SAFE")
    risk_score = Column(Integer, default=0)
    status = Column(String(50), default="SCANNED")
    created_at = Column(DateTime, server_default=func.now())

# ================================================================================
# 14. QUARANTINE MODEL
# ================================================================================
class QuarantineTable(Base):
    __tablename__ = "apt_quarantine_b"

    quarantine_id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(Integer, nullable=True)
    file_name = Column(String(255), nullable=False)
    package_name = Column(String(255), nullable=True)
    threat_level = Column(String(50), default="HIGH_RISK")
    quarantined_at = Column(DateTime, server_default=func.now())

# ================================================================================
# 15. UNLINK CODES MODEL (MATCHES apt.apt_unlink_codes_b)
# ================================================================================
class UnlinkCodeTable(Base):
    __tablename__ = "apt_unlink_codes_b"

    unlink_id = Column("unlink_id", Integer, primary_key=True, autoincrement=True)
    unlink_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4)
    parent_id = Column("parent_id", Integer, nullable=True)
    child_id = Column("child_id", Integer, nullable=False, index=True)
    pairing_uuid = Column(UUID(as_uuid=True), nullable=True)
    unlink_code = Column(String(20), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    status = Column(String(20), default="PENDING")
    is_used = Column(Boolean, default=False, nullable=False)
    created_by = Column(String(255), default="SYSTEM")
    created_date = Column(DateTime, server_default=func.now())
    last_updated_by = Column(String(255), default="SYSTEM")
    last_updated_date = Column(DateTime, server_default=func.now())

# ================================================================================
# 16. INSTALLED APPLICATIONS MODEL (MATCHES apt.apt_installed_apps_b)
# ================================================================================


class ChildApp(Base):
    __tablename__ = "apt_child_apps_b"
    __table_args__ = (
        UniqueConstraint("child_id", "package_name", name="uq_child_apps_pkg"),
        {"schema": "apt"}  # <--- Ensures queries target the 'apt' schema
    )

    # Primary key mapped to DB team's column name
    child_app_id = Column("child_app_id", BigInteger, primary_key=True, autoincrement=True)
    child_app_uuid = Column("child_app_uuid", UUID(as_uuid=True), default=uuid.uuid4)
    child_id = Column(BigInteger, ForeignKey("apt.apt_children_b.child_id", ondelete="CASCADE"), nullable=False)
    
    # Metadata columns
    package_name = Column(String(255), nullable=True)
    app_name = Column(String(255), nullable=True)
    category = Column(String(100), default="General")
    is_blocked = Column(Boolean, default=False, nullable=False)
    daily_limit_minutes = Column(Integer, default=-1)
    is_always_allowed = Column(Boolean, default=False)
    minutes_used_today = Column(Integer, default=0)
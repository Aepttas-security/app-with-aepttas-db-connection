# models.py - Fixed to match database schema
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, ForeignKey, UUID, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid
from database import Base


# ============================================
# 1. USERS TABLE
# ============================================
class AptUsersB(Base):
    __tablename__ = 'apt_users_b'
    __table_args__ = {'schema': 'apt'}
    
    user_id = Column(BigInteger, primary_key=True, index=True)
    user_uuid = Column(UUID, default=uuid.uuid4, nullable=False)
    username = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    created_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    created_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_updated_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_updated_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_dml_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_dml_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_ddl_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_ddl_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    program_id = Column(BigInteger)
    
    calls = relationship("AptCallsB", foreign_keys="AptCallsB.user_id", back_populates="user")
    alerts = relationship("AptAlertsB", foreign_keys="AptAlertsB.user_id", back_populates="user")
    reports = relationship("AptReportsB", foreign_keys="AptReportsB.user_id", back_populates="user")
    blocked_numbers = relationship("AptBlockedNumbersB", foreign_keys="AptBlockedNumbersB.user_id", back_populates="user")
    settings = relationship("AptCallSettingsB", foreign_keys="AptCallSettingsB.user_id", back_populates="user", uselist=False)


# ============================================
# 2. CALLERS
# ============================================
class AptCallersB(Base):
    __tablename__ = 'apt_callers_b'
    __table_args__ = {'schema': 'apt'}
    
    caller_id = Column(BigInteger, primary_key=True, index=True)
    caller_uuid = Column(UUID, default=uuid.uuid4, nullable=False)
    phone_number = Column(String(20), nullable=False)
    caller_name = Column(String(200))
    is_spam_reported = Column(Boolean, default=False, nullable=False)
    risk_level_id = Column(BigInteger)
    created_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    created_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_updated_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_updated_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_dml_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_dml_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_ddl_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_ddl_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    program_id = Column(BigInteger)
    
    calls = relationship("AptCallsB", foreign_keys="AptCallsB.caller_id", back_populates="caller")
    alerts = relationship("AptAlertsB", foreign_keys="AptAlertsB.caller_id", back_populates="caller")
    reports = relationship("AptReportsB", foreign_keys="AptReportsB.caller_id", back_populates="caller")
    blocked_numbers = relationship("AptBlockedNumbersB", foreign_keys="AptBlockedNumbersB.caller_id", back_populates="caller")


# ============================================
# 3. CALLS
# ============================================
class AptCallsB(Base):
    __tablename__ = 'apt_calls_b'
    __table_args__ = {'schema': 'apt'}
    
    call_id = Column(BigInteger, primary_key=True, index=True)
    call_uuid = Column(UUID, default=uuid.uuid4, nullable=False)
    user_id = Column(BigInteger, ForeignKey('apt.apt_users_b.user_id'), nullable=False)
    caller_id = Column(BigInteger, ForeignKey('apt.apt_callers_b.caller_id'), nullable=False)
    phone_number = Column(String(20), nullable=False)
    call_type = Column(String(20), nullable=False)
    call_duration_seconds = Column(Integer, default=0, nullable=False)
    call_timestamp = Column(DateTime(timezone=True), nullable=False)
    status_id = Column(BigInteger)
    created_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    created_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_updated_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_updated_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_dml_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_dml_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_ddl_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_ddl_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    program_id = Column(BigInteger)
    
    user = relationship("AptUsersB", foreign_keys=[user_id], back_populates="calls")
    caller = relationship("AptCallersB", foreign_keys=[caller_id], back_populates="calls")
    alerts = relationship("AptAlertsB", foreign_keys="AptAlertsB.call_id", back_populates="call")
    reports = relationship("AptReportsB", foreign_keys="AptReportsB.call_id", back_populates="call")


# ============================================
# 4. BLOCKED NUMBERS (FIXED)
# ============================================
class AptBlockedNumbersB(Base):
    __tablename__ = 'apt_blocked_numbers_b'
    __table_args__ = {'schema': 'apt'}
    
    blocked_number_id = Column(BigInteger, primary_key=True, index=True)
    blocked_number_uuid = Column(UUID, default=uuid.uuid4, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    caller_id = Column(BigInteger, ForeignKey('apt.apt_callers_b.caller_id'), nullable=False)
    phone_number = Column(String(20), nullable=False)
    blocked_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reason = Column(String(255))  # ✅ FIXED: Changed from 500 to 255
    created_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    created_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_updated_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_updated_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_dml_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_dml_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_ddl_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_ddl_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    program_id = Column(BigInteger)
    
    user = relationship("AptUsersB", foreign_keys=[user_id], back_populates="blocked_numbers")
    caller = relationship("AptCallersB", foreign_keys=[caller_id], back_populates="blocked_numbers")


# ============================================
# 5. ALERTS
# ============================================
class AptAlertsB(Base):
    __tablename__ = 'apt_alerts_b'
    __table_args__ = {'schema': 'apt'}
    
    alert_id = Column(BigInteger, primary_key=True, index=True)
    alert_uuid = Column(UUID, default=uuid.uuid4, nullable=False)
    user_id = Column(BigInteger, ForeignKey('apt.apt_users_b.user_id'), nullable=False)
    caller_id = Column(BigInteger, ForeignKey('apt.apt_callers_b.caller_id'), nullable=True)
    call_id = Column(BigInteger, ForeignKey('apt.apt_calls_b.call_id'), nullable=True)
    phone_number = Column(String(20), nullable=True)
    severity_id = Column(BigInteger, nullable=False)
    alert_message = Column(String(1000), nullable=False)
    is_acknowledged = Column(Boolean, default=False, nullable=False)
    created_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    created_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_updated_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_updated_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_dml_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_dml_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_ddl_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_ddl_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    program_id = Column(BigInteger)
    
    user = relationship("AptUsersB", foreign_keys=[user_id], back_populates="alerts")
    caller = relationship("AptCallersB", foreign_keys=[caller_id], back_populates="alerts")
    call = relationship("AptCallsB", foreign_keys=[call_id], back_populates="alerts")


# ============================================
# 6. REPORTS
# ============================================
class AptReportsB(Base):
    __tablename__ = 'apt_reports_b'
    __table_args__ = {'schema': 'apt'}
    
    report_id = Column(BigInteger, primary_key=True, index=True)
    report_uuid = Column(UUID, default=uuid.uuid4, nullable=False)
    user_id = Column(BigInteger, ForeignKey('apt.apt_users_b.user_id'), nullable=False)
    caller_id = Column(BigInteger, ForeignKey('apt.apt_callers_b.caller_id'), nullable=False)
    call_id = Column(BigInteger, ForeignKey('apt.apt_calls_b.call_id'), nullable=True)
    phone_number = Column(String(20), nullable=False)
    report_reason = Column(String(500), nullable=False)
    status_id = Column(BigInteger)
    created_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    created_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_updated_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_updated_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_dml_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_dml_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_ddl_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_ddl_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    program_id = Column(BigInteger)
    
    user = relationship("AptUsersB", foreign_keys=[user_id], back_populates="reports")
    caller = relationship("AptCallersB", foreign_keys=[caller_id], back_populates="reports")
    call = relationship("AptCallsB", foreign_keys=[call_id], back_populates="reports")


# ============================================
# 7. CALL SETTINGS
# ============================================
class AptCallSettingsB(Base):
    __tablename__ = 'apt_call_settings_b'
    __table_args__ = {'schema': 'apt'}
    
    call_setting_id = Column(BigInteger, primary_key=True, index=True)
    call_setting_uuid = Column(UUID, default=uuid.uuid4, nullable=False)
    user_id = Column(BigInteger, ForeignKey('apt.apt_users_b.user_id'), nullable=False)
    auto_block_spam = Column(Boolean, default=True, nullable=False)
    block_unknown_numbers = Column(Boolean, default=False, nullable=False)
    notification_type_id = Column(BigInteger)
    created_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    created_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_updated_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_updated_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_dml_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_dml_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_ddl_by = Column(String(100), server_default='CURRENT_USER', nullable=False)
    last_ddl_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    program_id = Column(BigInteger)
    
    user = relationship("AptUsersB", foreign_keys=[user_id], back_populates="settings")
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


# ==========================================================
# GEOLOCATION
# ==========================================================
class AptUser(Base):
    __tablename__ = "apt_users_b"
    __table_args__ = {"schema": "apt"}

    user_id = Column(BigInteger, primary_key=True)


class AptProgram(Base):
    __tablename__ = "apt_programs_b"
    __table_args__ = {"schema": "apt"}

    program_id = Column(BigInteger, primary_key=True)


class GeolocationScan(Base):
    __tablename__ = "apt_location_records_b"
    __table_args__ = (
        CheckConstraint(
            "spoof_confidence IN ('low','medium','high')",
            name="ck_spoof_confidence",
        ),
        {"schema": "apt"},
    )

    location_record_id = Column(
        BigInteger,
        primary_key=True,
        index=True,
        server_default=text("generated always as identity"),
    )

    location_record_uuid = Column(
        UUID(as_uuid=True),
        nullable=False,
        server_default=text("gen_random_uuid()"),
    )

    device_id = Column(String(128), nullable=False)

    latitude = Column(Float, nullable=False)

    longitude = Column(Float, nullable=False)

    accuracy = Column(Float)

    speed_kmh = Column(Float)

    provider = Column(String(32))

    platform = Column(String(16))

    app_version = Column(String(32))

    city = Column(String(128))

    country = Column(String(128))

    address = Column(Text)

    gps_timestamp = Column(DateTime(timezone=True), nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    is_spoofed = Column(Boolean)

    spoof_confidence = Column(String(32))

    spoof_reasons = Column(
        JSONB,
        server_default=text("'[]'::jsonb"),
    )

    raw_provider_flags = Column(
        JSONB,
        server_default=text("'{}'::jsonb"),
    )

    user_id = Column(
        BigInteger,
        ForeignKey("apt.apt_users_b.user_id"),
    )

    program_id = Column(
        BigInteger,
        ForeignKey("apt.apt_programs_b.program_id"),
    )

    is_active = Column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    attributes = Column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    created_by = Column(
        String(100),
        nullable=False,
        server_default=text("CURRENT_USER"),
    )

    last_updated_by = Column(
        String(100),
        nullable=False,
        server_default=text("CURRENT_USER"),
    )

    last_updated_date = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    last_dml_by = Column(
        String(100),
        nullable=False,
        server_default=text("CURRENT_USER"),
    )

    last_dml_date = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    last_ddl_by = Column(
        String(100),
        nullable=False,
        server_default=text("CURRENT_USER"),
    )

    last_ddl_date = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


# ==========================================================
# NEARBY PLACES
# ==========================================================

class NearbyPlace(Base):
    __tablename__ = "apt_nearby_places_b"
    __table_args__ = {"schema": "apt"}

    nearby_place_id = Column(
        BigInteger,
        primary_key=True,
        index=True,
        server_default=text("generated always as identity"),
    )

    nearby_place_uuid = Column(
        UUID(as_uuid=True),
        nullable=False,
        server_default=text("gen_random_uuid()"),
    )

    place_name = Column(String(255), nullable=False)

    place_type = Column(String(32), nullable=False)

    latitude = Column(Float, nullable=False)

    longitude = Column(Float, nullable=False)

    address = Column(Text)

    city = Column(String(128))

    country = Column(String(128))

    is_active = Column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    attributes = Column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    created_by = Column(
        String(100),
        nullable=False,
        server_default=text("CURRENT_USER"),
    )

    created_date = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    last_updated_by = Column(
        String(100),
        nullable=False,
        server_default=text("CURRENT_USER"),
    )

    last_updated_date = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    last_dml_by = Column(
        String(100),
        nullable=False,
        server_default=text("CURRENT_USER"),
    )

    last_dml_date = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    last_ddl_by = Column(
        String(100),
        nullable=False,
        server_default=text("CURRENT_USER"),
    )

    last_ddl_date = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    program_id = Column(
        BigInteger,
        ForeignKey("apt.apt_programs_b.program_id"),
    )


# ==========================================================
# LEGACY LOCAL TABLE (Optional)
# ==========================================================

class SavedLocation(Base):
    __tablename__ = "saved_locations"

    id = Column(Integer, primary_key=True, index=True)

    device_id = Column(String, nullable=False)

    latitude = Column(Float, nullable=False)

    longitude = Column(Float, nullable=False)

    accuracy = Column(Float, default=0.0)

    city = Column(String)

    country = Column(String)

    address = Column(String)

    timestamp = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
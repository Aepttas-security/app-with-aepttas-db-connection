package com.aepttas.shield.db;

import androidx.room.Dao;
import androidx.room.Insert;
import androidx.room.Query;

import java.util.List;
import java.util.UUID;

/**
 * DAO for apt_calls_b table.
 * Includes JOIN query with apt_callers_b for Prompt 9 (Call History screen).
 */
@Dao
public interface AptCallsDao {

    @Insert
    void insert(AptCallsEntity call);

    @Query("SELECT * FROM apt_calls_b ORDER BY call_timestamp DESC")
    List<AptCallsEntity> getAllHistory();

    @Query("SELECT * FROM apt_calls_b WHERE is_synced = 0")
    List<AptCallsEntity> getUnsyncedHistory();

    @Query("SELECT * FROM apt_calls_b WHERE status = :status ORDER BY call_timestamp DESC")
    List<AptCallsEntity> getByStatus(String status);

    @Query("UPDATE apt_calls_b SET is_synced = 1 WHERE call_uuid = :uuid")
    void markAsSynced(java.util.UUID uuid);

    @Query("DELETE FROM apt_calls_b")
    void deleteAll();

    // ── PROMPT 9: Call History with caller info ──────────────────
    /**
     * LEFT JOIN apt_calls_b ↔ apt_callers_b on phone_number.
     * Returns combined call history items sorted newest-first.
     * Uses COALESCE to supply defaults when caller is unknown.
     * Maps into CallHistoryItem POJO (not an @Entity).
     */
    @Query("SELECT " +
           "  c.call_uuid, " +
           "  c.phone_number, " +
           "  COALESCE(ca.caller_name, c.caller_name, 'Unknown Caller') AS caller_name, " +
           "  c.call_type, " +
           "  c.call_duration_seconds, " +
           "  c.call_timestamp, " +
           "  COALESCE(ca.risk_score, 50) AS risk_score, " +
           "  COALESCE(ca.is_spam, 0) AS is_spam, " +
           "  COALESCE(ca.is_blocked, 0) AS is_blocked, " +
           "  COALESCE(ca.carrier, 'Unknown') AS carrier, " +
           "  COALESCE(ca.location, 'Unknown') AS location " +
           "FROM apt_calls_b c " +
           "LEFT JOIN apt_callers_b ca ON c.phone_number = ca.phone_number " +
           "ORDER BY c.call_timestamp DESC")
    List<CallHistoryItem> getAllHistoryWithCallerInfo();

    /** Get count of calls by type (useful for analytics) */
    @Query("SELECT COUNT(*) FROM apt_calls_b WHERE call_type = :callType")
    int getCountByType(String callType);
}
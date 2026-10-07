package com.aepttas.shield.db;

import androidx.room.ColumnInfo;

import java.util.Date;
import java.util.UUID;

/**
 * POJO result for the JOIN query between apt_calls_b and apt_callers_b.
 * NOT a Room @Entity — does NOT create or modify any database table.
 * Used only for reading combined call history data.
 */
public class CallHistoryItem {

    @ColumnInfo(name = "call_uuid")
    public UUID callUuid;

    @ColumnInfo(name = "phone_number")
    public String phoneNumber;

    // From apt_calls_b (stored at call time)
    @ColumnInfo(name = "caller_name")
    public String callerName;

    @ColumnInfo(name = "call_type")
    public String callType;

    @ColumnInfo(name = "call_duration_seconds")
    public int callDurationSeconds;

    @ColumnInfo(name = "call_timestamp")
    public Date callTimestamp;

    // From apt_callers_b (joined, may be null for unknown numbers)
    @ColumnInfo(name = "risk_score")
    public int riskScore;

    @ColumnInfo(name = "is_spam")
    public boolean isSpam;

    @ColumnInfo(name = "is_blocked")
    public boolean isBlocked;

    @ColumnInfo(name = "carrier")
    public String carrier;

    @ColumnInfo(name = "location")
    public String location;
}

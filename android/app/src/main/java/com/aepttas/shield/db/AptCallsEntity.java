package com.aepttas.shield.db;

import androidx.annotation.NonNull;
import androidx.room.ColumnInfo;
import androidx.room.Entity;
import androidx.room.PrimaryKey;

import java.util.Date;
import java.util.UUID;

@Entity(tableName = "apt_calls_b")
public class AptCallsEntity {

    @PrimaryKey
    @NonNull
    @ColumnInfo(name = "call_uuid")
    public UUID callUuid;

    @ColumnInfo(name = "user_id")
    public long userId;

    @ColumnInfo(name = "caller_id")
    public long callerId;

    @NonNull
    @ColumnInfo(name = "phone_number")
    public String phoneNumber;

    @ColumnInfo(name = "caller_name")
    public String callerName;

    @ColumnInfo(name = "call_type")
    public String callType;

    @ColumnInfo(name = "call_duration_seconds")
    public int callDurationSeconds;

    @ColumnInfo(name = "call_timestamp")
    public Date callTimestamp;

    @ColumnInfo(name = "is_synced")
    public boolean isSynced;

    @ColumnInfo(name = "status")
    public String status;

    public AptCallsEntity() {
        this.callUuid = UUID.randomUUID();
        this.callTimestamp = new Date();
        this.isSynced = false;
        this.status = "INCOMING";
        this.userId = 1; // Default user ID as per backend get_uid()
    }
}
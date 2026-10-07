package com.aepttas.shield.db;

import androidx.annotation.NonNull;
import androidx.room.ColumnInfo;
import androidx.room.Entity;
import androidx.room.PrimaryKey;

import java.util.Date;
import java.util.UUID;

@Entity(tableName = "spam_report_log")
public class SpamReportEntity {
    @PrimaryKey
    @NonNull
    @ColumnInfo(name = "id")
    public UUID id;

    @NonNull
    @ColumnInfo(name = "phone_number")
    public String phoneNumber;

    @ColumnInfo(name = "caller_name")
    public String callerName;

    @ColumnInfo(name = "report_type")
    public String reportType;

    @ColumnInfo(name = "reported_by")
    public String reportedBy;

    @ColumnInfo(name = "reported_at")
    public Date reportedAt;

    public SpamReportEntity() {
        id = UUID.randomUUID();
        reportedAt = new Date();
    }
}

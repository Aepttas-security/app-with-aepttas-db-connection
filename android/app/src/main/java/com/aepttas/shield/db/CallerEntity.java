package com.aepttas.shield.db;

import androidx.annotation.NonNull;
import androidx.room.ColumnInfo;
import androidx.room.Entity;
import androidx.room.Index;
import androidx.room.PrimaryKey;

import java.util.Date;
import java.util.UUID;

@Entity(tableName = "apt_callers_b", indices = {@Index(value = {"phone_number"}, unique = true)})
public class CallerEntity {
    
    @PrimaryKey
    @NonNull
    @ColumnInfo(name = "id")
    public UUID id;

    @NonNull
    @ColumnInfo(name = "phone_number")
    public String phoneNumber;

    @ColumnInfo(name = "caller_name")
    public String callerName;

    @ColumnInfo(name = "carrier")
    public String carrier;

    @ColumnInfo(name = "location")
    public String location;

    @ColumnInfo(name = "risk_score")
    public int riskScore;

    @ColumnInfo(name = "total_reports")
    public int totalReports;

    @ColumnInfo(name = "is_spam")
    public boolean isSpam;

    @ColumnInfo(name = "is_blocked")
    public boolean isBlocked;

    @ColumnInfo(name = "created_at")
    public Date createdAt;

    @ColumnInfo(name = "updated_at")
    public Date updatedAt;

    public CallerEntity() {
        this.id = UUID.randomUUID();
        this.createdAt = new Date();
        this.updatedAt = new Date();
    }
}
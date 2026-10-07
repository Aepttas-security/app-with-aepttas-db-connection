package com.aepttas.shield.db;

import androidx.annotation.NonNull;
import androidx.room.ColumnInfo;
import androidx.room.Entity;
import androidx.room.PrimaryKey;

import java.util.Date;
import java.util.UUID;

@Entity(tableName = "alerts")
public class AlertEntity {
    @PrimaryKey
    @NonNull
    @ColumnInfo(name = "id")
    public UUID id;

    @ColumnInfo(name = "phone_number")
    public String phoneNumber;

    @ColumnInfo(name = "caller_name")
    public String callerName;

    @ColumnInfo(name = "alert_type")
    public String alertType;

    @ColumnInfo(name = "alert_message")
    public String alertMessage;

    @ColumnInfo(name = "created_at")
    public Date createdAt;

    @ColumnInfo(name = "is_read")
    public boolean isRead;

    public AlertEntity() {
        id = UUID.randomUUID();
        createdAt = new Date();
        isRead = false;
    }
}

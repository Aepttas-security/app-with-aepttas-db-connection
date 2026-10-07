package com.aepttas.shield.db;

import androidx.annotation.NonNull;
import androidx.room.ColumnInfo;
import androidx.room.Entity;
import androidx.room.Index;
import androidx.room.PrimaryKey;

import java.util.Date;
import java.util.UUID;

@Entity(tableName = "apt_blocked_numbers", indices = {@Index(value = {"phone_number"}, unique = true)})
public class BlockedNumberEntity {
    @PrimaryKey
    @NonNull
    @ColumnInfo(name = "id")
    public UUID id;

    @NonNull
    @ColumnInfo(name = "phone_number")
    public String phoneNumber;

    @ColumnInfo(name = "caller_name")
    public String callerName;

    @ColumnInfo(name = "block_reason")
    public String blockReason;

    @ColumnInfo(name = "block_date")
    public Date blockDate;

    public BlockedNumberEntity() {
        id = UUID.randomUUID();
        blockDate = new Date();
    }
}

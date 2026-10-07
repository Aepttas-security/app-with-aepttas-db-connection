package com.aepttas.shield.db;

import androidx.room.Dao;
import androidx.room.Insert;
import androidx.room.OnConflictStrategy;
import androidx.room.Query;

import java.util.List;

@Dao
public interface BlockedNumberDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    void insert(BlockedNumberEntity blockedNumber);

    @Query("SELECT * FROM apt_blocked_numbers ORDER BY block_date DESC")
    List<BlockedNumberEntity> getAll();

    @Query("SELECT * FROM apt_blocked_numbers WHERE phone_number = :phoneNumber LIMIT 1")
    BlockedNumberEntity getByPhoneNumber(String phoneNumber);

    @Query("DELETE FROM apt_blocked_numbers WHERE phone_number = :phoneNumber")
    void deleteByPhoneNumber(String phoneNumber);
}

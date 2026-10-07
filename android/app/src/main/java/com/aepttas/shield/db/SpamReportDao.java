package com.aepttas.shield.db;

import androidx.room.Dao;
import androidx.room.Insert;
import androidx.room.OnConflictStrategy;
import androidx.room.Query;

import java.util.List;

@Dao
public interface SpamReportDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    void insert(SpamReportEntity report);

    @Query("SELECT * FROM spam_report_log ORDER BY reported_at DESC")
    List<SpamReportEntity> getAll();

    @Query("SELECT * FROM spam_report_log WHERE phone_number = :phoneNumber ORDER BY reported_at DESC")
    List<SpamReportEntity> getAllByPhone(String phoneNumber);

    @Query("DELETE FROM spam_report_log WHERE id = :id")
    void deleteById(String id);

    @Query("DELETE FROM spam_report_log WHERE phone_number = :phoneNumber")
    void deleteByPhoneNumber(String phoneNumber);
}

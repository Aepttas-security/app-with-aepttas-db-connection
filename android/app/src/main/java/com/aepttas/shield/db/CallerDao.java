package com.aepttas.shield.db;

import androidx.room.Dao;
import androidx.room.Insert;
import androidx.room.OnConflictStrategy;
import androidx.room.Query;
import androidx.room.Update;

import java.util.List;

@Dao
public interface CallerDao {
    @Query("SELECT * FROM apt_callers_b WHERE phone_number = :phoneNumber LIMIT 1")
    CallerEntity getByPhoneNumber(String phoneNumber);

    @Query("SELECT * FROM apt_callers_b WHERE phone_number LIKE '%' || :query || '%' OR caller_name LIKE '%' || :query || '%'")
    List<CallerEntity> searchFuzzy(String query);

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    void insertOrUpdate(CallerEntity caller);

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    void insertAll(List<CallerEntity> callers);

    @Update
    void update(CallerEntity caller);

    @Query("DELETE FROM apt_callers_b")
    void deleteAll();

    // --- Analytics Methods ---
    
    @Query("SELECT COUNT(*) FROM apt_callers_b")
    int getTotalContacts();

    @Query("SELECT COUNT(*) FROM apt_callers_b WHERE is_spam = 1")
    int getSpamCount();

    @Query("SELECT COUNT(*) FROM apt_callers_b WHERE is_blocked = 1")
    int getBlockedCount();

    @Query("SELECT AVG(risk_score) FROM apt_callers_b")
    double getAvgRiskScore();

    @Query("SELECT SUM(total_reports) FROM apt_callers_b")
    int getTotalReportsSum();
}
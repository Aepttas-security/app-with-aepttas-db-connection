package com.aepttas.shield.db;

import androidx.room.Dao;
import androidx.room.Insert;
import androidx.room.OnConflictStrategy;
import androidx.room.Query;

import java.util.List;

@Dao
public interface AlertDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    void insert(AlertEntity alert);

    @Query("SELECT * FROM alerts ORDER BY created_at DESC")
    List<AlertEntity> getAll();
}

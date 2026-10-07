package com.aepttas.shield.db;

import android.content.Context;

import androidx.room.Database;
import androidx.room.Room;
import androidx.room.RoomDatabase;
import androidx.room.TypeConverters;

@Database(entities = {
    CallerEntity.class,
    AptCallsEntity.class,
    BlockedNumberEntity.class,
    SpamReportEntity.class,
    AlertEntity.class
}, version = 4, exportSchema = false)
@TypeConverters({Converters.class})
public abstract class ShieldDatabase extends RoomDatabase {
    private static volatile ShieldDatabase INSTANCE;

    public abstract CallerDao callerDao();
    public abstract AptCallsDao aptCallsDao();
    public abstract BlockedNumberDao blockedNumberDao();
    public abstract SpamReportDao spamReportDao();
    public abstract AlertDao alertDao();

    public static ShieldDatabase getDatabase(final Context context) {
        if (INSTANCE == null) {
            synchronized (ShieldDatabase.class) {
                if (INSTANCE == null) {
                    INSTANCE = Room.databaseBuilder(context.getApplicationContext(),
                                    ShieldDatabase.class, "shield_database")
                            .fallbackToDestructiveMigration()
                            .build();
                }
            }
        }
        return INSTANCE;
    }
}
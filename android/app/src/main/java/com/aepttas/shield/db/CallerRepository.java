package com.aepttas.shield.db;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;

import com.aepttas.shield.services.ContactLookupService;

import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class CallerRepository {
    private final CallerDao callerDao;
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    public CallerRepository(Context context) {
        ShieldDatabase db = ShieldDatabase.getDatabase(context);
        callerDao = db.callerDao();
    }

    public interface Callback<T> {
        void onComplete(T result);
    }

    public void searchCallers(String query, Callback<List<CallerEntity>> callback) {
        executor.execute(() -> {
            List<CallerEntity> results = callerDao.searchFuzzy(query);
            mainHandler.post(() -> callback.onComplete(results));
        });
    }

    public void getAnalytics(Callback<AnalyticsStats> callback) {
        executor.execute(() -> {
            AnalyticsStats stats = new AnalyticsStats();
            stats.totalContacts = callerDao.getTotalContacts();
            stats.spamCount = callerDao.getSpamCount();
            stats.blockedCount = callerDao.getBlockedCount();
            stats.avgRiskScore = callerDao.getAvgRiskScore();
            stats.totalReportsSum = callerDao.getTotalReportsSum();
            mainHandler.post(() -> callback.onComplete(stats));
        });
    }

    public static class AnalyticsStats {
        public int totalContacts;
        public int spamCount;
        public int blockedCount;
        public double avgRiskScore;
        public int totalReportsSum;
    }
}
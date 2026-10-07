package com.aepttas.shield.workers;

import android.content.Context;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import com.aepttas.shield.constants.Config;
import com.aepttas.shield.db.CallerDao;
import com.aepttas.shield.db.CallerEntity;
import com.aepttas.shield.db.ShieldDatabase;

import java.net.HttpURLConnection;
import java.net.URL;

public class RiskScoreWorker extends Worker {
    private static final String TAG = "RiskScoreWorker";

    public RiskScoreWorker(@NonNull Context context, @NonNull WorkerParameters workerParams) {
        super(context, workerParams);
    }

    @NonNull
    @Override
    public Result doWork() {
        try {
            Log.d(TAG, "⏰ WorkManager: Updating Local Risk Scores...");
            CallerDao dao = ShieldDatabase.getDatabase(getApplicationContext()).callerDao();
            
            // In a real implementation, we would fetch all or a subset to update.
            // For this logic: risk_score = min(total_reports * 5, 100)
            
            // We'll sync this logic with the backend
            URL url = new URL(Config.BACKEND_URL + "/api/callers/risk/update-all");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("PUT");
            conn.setRequestProperty("X-API-Key", Config.API_KEY);
            
            int code = conn.getResponseCode();
            Log.d(TAG, "📤 Remote Risk Update Status: " + code);
            conn.disconnect();
            
            return Result.success();
        } catch (Exception e) {
            Log.e(TAG, "❌ RiskScoreWorker Error: " + e.getMessage());
            return Result.retry();
        }
    }
}
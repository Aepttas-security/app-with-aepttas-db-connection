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
import com.aepttas.shield.services.AutoBlockService;

import org.json.JSONArray;
import org.json.JSONObject;

import java.net.HttpURLConnection;
import java.net.URL;
import java.util.Scanner;

public class AutoBlockWorker extends Worker {
    private static final String TAG = "AutoBlockWorker";

    public AutoBlockWorker(@NonNull Context context, @NonNull WorkerParameters workerParams) {
        super(context, workerParams);
    }

    @NonNull
    @Override
    public Result doWork() {
        try {
            Log.d(TAG, "⏰ WorkManager: Starting Auto-Block Audit...");
            
            // 1. Fetch high-report numbers from backend
            URL url = new URL(Config.BACKEND_URL + "/api/callers/audit/spam");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setRequestProperty("X-API-Key", Config.API_KEY);

            if (conn.getResponseCode() == 200) {
                Scanner s = new Scanner(conn.getInputStream()).useDelimiter("\\A");
                String result = s.hasNext() ? s.next() : "";
                JSONArray callers = new JSONArray(result);
                
                CallerDao dao = ShieldDatabase.getDatabase(getApplicationContext()).callerDao();

                for (int i = 0; i < callers.length(); i++) {
                    JSONObject obj = callers.getJSONObject(i);
                    String phone = obj.getString("phone_number");
                    int reports = obj.getInt("total_reports");
                    
                    if (reports > 10) {
                        CallerEntity entity = dao.getByPhoneNumber(phone);
                        if (entity == null) {
                            entity = new CallerEntity();
                            entity.phoneNumber = phone;
                            entity.callerName = obj.optString("caller_name", "Spammer");
                        }
                        entity.totalReports = reports;
                        entity.riskScore = Math.min(reports * 5, 100);
                        
                        dao.insertOrUpdate(entity);
                        // Execute block logic after persisting the current caller.
                        AutoBlockService.checkAndBlock(getApplicationContext(), entity);
                    }
                }
            }
            conn.disconnect();
            return Result.success();
            
        } catch (Exception e) {
            Log.e(TAG, "❌ AutoBlockWorker Error: " + e.getMessage());
            return Result.retry();
        }
    }
}
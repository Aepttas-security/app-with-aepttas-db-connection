package com.aepttas.shield.helpers;

import android.content.Context;
import android.util.Log;
import android.widget.Toast;

import com.aepttas.shield.constants.Config;

import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class SpamReportHelper {
    private static final String TAG = "SpamReportHelper";
    private static final ExecutorService executor = Executors.newSingleThreadExecutor();

    public static void reportSpam(Context context, String phoneNumber, String category, String comment) {
        // 🛡️ Technique 5: Spam Report Using apt.apt_callers_b
        executor.execute(() -> {
            try {
                // API: POST /api/callers/report
                URL url = new URL(Config.BACKEND_URL + "/api/callers/report");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setRequestProperty("X-API-Key", Config.API_KEY);
                conn.setDoOutput(true);

                JSONObject report = new JSONObject();
                report.put("number", phoneNumber);
                report.put("phone_number", phoneNumber);
                report.put("caller_name", "Unknown");
                report.put("category", category);
                report.put("report_type", category);
                report.put("comment", comment);
                report.put("timestamp", System.currentTimeMillis());

                try (OutputStream os = conn.getOutputStream()) {
                    byte[] input = report.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8);
                    os.write(input, 0, input.length);
                }

                int code = conn.getResponseCode();
                if (code == 200 || code == 201) {
                    new android.os.Handler(android.os.Looper.getMainLooper()).post(() -> {
                        Toast.makeText(context, "Shield: Spam reported. Community protected!", Toast.LENGTH_SHORT).show();
                    });
                } else {
                    Log.e(TAG, "❌ Failed to report spam. Code: " + code);
                }
                conn.disconnect();
            } catch (Exception e) {
                Log.e(TAG, "❌ Report Error: " + e.getMessage());
            }
        });
    }
}
package com.aepttas.shield.services;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.widget.Toast;

import com.aepttas.shield.constants.Config;
import com.aepttas.shield.db.CallerDao;
import com.aepttas.shield.db.CallerEntity;
import com.aepttas.shield.db.ShieldDatabase;
import com.aepttas.shield.helpers.NotificationHelper;

import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * PROMPT 6 – Block Service
 *
 * Handles the full block flow:
 * 1) Update apt.apt_callers_b → is_blocked = true  (via POST /api/callers/block)
 * 2) Insert into apt.apt_blocked_numbers            (via POST /api/blocked/add)
 * 3) Insert into apt.alerts                         (via POST /api/alerts)
 * 4) Update local Room cache (CallerEntity.isBlocked = true)
 * 5) Show Toast "Number Blocked"
 */
public class BlockService {
    private static final String TAG = "BlockService";
    private static final ExecutorService executor = Executors.newCachedThreadPool();

    // ─────────────────────────────────────────────────────────────
    // Public entry point
    // ─────────────────────────────────────────────────────────────

    public static void blockNumber(Context context, String phoneNumber, String callerName) {
        if (phoneNumber == null || phoneNumber.isEmpty()) return;

        executor.execute(() -> {
            boolean success = false;

            // STEP 1 ── Update apt.apt_callers_b  (set is_blocked = true)
            success = updateCallerBlockStatus(phoneNumber, callerName);

            // STEP 2 ── Insert into apt.apt_blocked_numbers
            insertIntoBlockedNumbers(phoneNumber, callerName);

            // STEP 3 ── Insert into apt.alerts
            insertAlert(phoneNumber, callerName,
                    "BLOCKED", "Number blocked by user");

            // STEP 4 ── Update local Room cache
            updateRoomCache(context, phoneNumber);
            cacheBlockedNumber(context, phoneNumber, callerName);

            // STEP 5 ── Toast
            final boolean ok = success;
            new Handler(Looper.getMainLooper()).post(() ->
                    Toast.makeText(context,
                            ok ? "🚫 Number Blocked" : "🚫 Block request sent",
                            Toast.LENGTH_SHORT).show()
            );

            Log.i(TAG, "✅ Block flow complete for: " + phoneNumber);
        });
    }

    // ─────────────────────────────────────────────────────────────
    // Step helpers
    // ─────────────────────────────────────────────────────────────

    /**
     * POST /api/callers/block → sets is_blocked = true in apt.apt_callers_b
     */
    private static boolean updateCallerBlockStatus(String phoneNumber, String callerName) {
        try {
            URL url = new URL(Config.BACKEND_URL + "/api/callers/block");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setRequestProperty("X-API-Key", Config.API_KEY);
            conn.setDoOutput(true);
            conn.setConnectTimeout(8000);
            conn.setReadTimeout(8000);

            JSONObject body = new JSONObject();
            body.put("phone_number", phoneNumber);
            body.put("caller_name", callerName != null ? callerName : "");
            body.put("is_blocked", true);
            body.put("reason", "User blocked");

            try (OutputStream os = conn.getOutputStream()) {
                os.write(body.toString().getBytes("utf-8"));
            }

            int code = conn.getResponseCode();
            Log.d(TAG, "📤 Block status update: HTTP " + code);
            conn.disconnect();
            return (code == 200 || code == 201);
        } catch (Exception e) {
            Log.e(TAG, "❌ updateCallerBlockStatus error: " + e.getMessage());
            return false;
        }
    }

    /**
     * POST /api/blocked/add → inserts into apt.apt_blocked_numbers
     */
    private static void insertIntoBlockedNumbers(String phoneNumber, String callerName) {
        try {
            URL url = new URL(Config.BACKEND_URL + "/api/blocked/add");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setRequestProperty("X-API-Key", Config.API_KEY);
            conn.setDoOutput(true);
            conn.setConnectTimeout(8000);
            conn.setReadTimeout(8000);

            JSONObject body = new JSONObject();
            body.put("phone_number", phoneNumber);
            body.put("caller_name", callerName != null ? callerName : "Unknown");
            body.put("block_reason", "User blocked");
            body.put("block_date", new java.text.SimpleDateFormat(
                    "yyyy-MM-dd'T'HH:mm:ss'Z'",
                    java.util.Locale.US).format(new java.util.Date()));

            try (OutputStream os = conn.getOutputStream()) {
                os.write(body.toString().getBytes("utf-8"));
            }

            int code = conn.getResponseCode();
            Log.d(TAG, "📤 apt_blocked_numbers insert: HTTP " + code);
            conn.disconnect();
        } catch (Exception e) {
            Log.e(TAG, "❌ insertIntoBlockedNumbers error: " + e.getMessage());
        }
    }

    /**
     * POST /api/alerts → inserts into apt.alerts table
     */
    public static void insertAlert(String phoneNumber, String callerName,
                                   String alertType, String alertMessage) {
        try {
            URL url = new URL(Config.BACKEND_URL + "/api/alerts");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setRequestProperty("X-API-Key", Config.API_KEY);
            conn.setDoOutput(true);
            conn.setConnectTimeout(8000);
            conn.setReadTimeout(8000);

            JSONObject body = new JSONObject();
            body.put("phone_number", phoneNumber != null ? phoneNumber : "");
            body.put("caller_name", callerName != null ? callerName : "Unknown");
            body.put("alert_type", alertType);
            body.put("alert_message", alertMessage);
            body.put("is_read", false);
            body.put("created_at", new java.text.SimpleDateFormat(
                    "yyyy-MM-dd'T'HH:mm:ss'Z'",
                    java.util.Locale.US).format(new java.util.Date()));

            try (OutputStream os = conn.getOutputStream()) {
                os.write(body.toString().getBytes("utf-8"));
            }

            int code = conn.getResponseCode();
            Log.d(TAG, "📤 alerts insert (" + alertType + "): HTTP " + code);
            conn.disconnect();
        } catch (Exception e) {
            Log.e(TAG, "❌ insertAlert error: " + e.getMessage());
        }
    }

    /**
     * Update local Room cache: set CallerEntity.isBlocked = true
     * so ScreeningService can block offline without an API call.
     */
    private static void updateRoomCache(Context context, String phoneNumber) {
        try {
            ShieldDatabase db = ShieldDatabase.getDatabase(context);
            CallerDao dao = db.callerDao();
            CallerEntity entity = dao.getByPhoneNumber(phoneNumber);
            if (entity != null) {
                entity.isBlocked = true;
                entity.updatedAt = new java.util.Date();
                dao.update(entity);
                Log.d(TAG, "✅ Room cache updated: isBlocked=true for " + phoneNumber);
            }
        } catch (Exception e) {
            Log.e(TAG, "❌ updateRoomCache error: " + e.getMessage());
        }
    }

    private static void cacheBlockedNumber(Context context, String phoneNumber, String callerName) {
        try {
            com.aepttas.shield.db.BlockedNumberEntity blocked =
                    new com.aepttas.shield.db.BlockedNumberEntity();
            blocked.phoneNumber = phoneNumber;
            blocked.callerName = callerName != null ? callerName : "Unknown";
            blocked.blockReason = "User blocked";
            ShieldDatabase.getDatabase(context).blockedNumberDao().insert(blocked);
        } catch (Exception e) {
            Log.e(TAG, "❌ Blocked-number cache error: " + e.getMessage());
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Static helper for ScreeningService offline check
    // ─────────────────────────────────────────────────────────────

    /**
     * Checks if a phone number is blocked.
     * First checks local Room cache (fast, offline-capable),
     * then falls back to API /api/blocked/check/{phone}.
     *
     * MUST be called from a background thread.
     */
    public static boolean isBlocked(Context context, String phoneNumber) {
        if (phoneNumber == null || phoneNumber.isEmpty()) return false;

        // 1. Local Room cache check (instant)
        try {
            CallerEntity entity = ShieldDatabase.getDatabase(context)
                    .callerDao().getByPhoneNumber(phoneNumber);
            if (entity != null && entity.isBlocked) {
                Log.d(TAG, "🔴 Room cache: " + phoneNumber + " is BLOCKED");
                return true;
            }
        } catch (Exception e) {
            Log.e(TAG, "Room check error: " + e.getMessage());
        }

        try {
            if (ShieldDatabase.getDatabase(context).blockedNumberDao()
                    .getByPhoneNumber(phoneNumber) != null) {
                Log.d(TAG, "🔴 Blocked-number cache: " + phoneNumber + " is BLOCKED");
                return true;
            }
        } catch (Exception e) {
            Log.e(TAG, "Blocked-number cache check error: " + e.getMessage());
        }

        // 2. Remote API check
        try {
            String encoded = java.net.URLEncoder.encode(phoneNumber, "UTF-8");
            URL url = new URL(Config.BACKEND_URL + "/api/blocked/check/" + encoded);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setRequestProperty("X-API-Key", Config.API_KEY);
            conn.setConnectTimeout(3000); // Fast timeout for screening
            conn.setReadTimeout(3000);

            int code = conn.getResponseCode();
            if (code == 200) {
                java.util.Scanner s = new java.util.Scanner(conn.getInputStream())
                        .useDelimiter("\\A");
                String result = s.hasNext() ? s.next() : "";
                conn.disconnect();

                JSONObject json = new JSONObject(result);
                boolean blocked = json.optBoolean("is_blocked", false);
                Log.d(TAG, "🌐 API check: " + phoneNumber + " blocked=" + blocked);
                return blocked;
            }
            conn.disconnect();
        } catch (Exception e) {
            Log.e(TAG, "❌ Remote block check error: " + e.getMessage());
        }
        return false;
    }
}

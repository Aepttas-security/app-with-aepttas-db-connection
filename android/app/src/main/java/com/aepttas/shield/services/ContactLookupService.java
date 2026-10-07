package com.aepttas.shield.services;

import android.content.Context;
import android.util.Log;

import com.aepttas.shield.constants.Config;
import com.aepttas.shield.db.CallerDao;
import com.aepttas.shield.db.CallerEntity;
import com.aepttas.shield.db.ShieldDatabase;

import org.json.JSONObject;

import java.net.HttpURLConnection;
import java.net.URL;
import java.util.Date;
import java.util.Scanner;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * PROMPT 2 – Fast Caller Lookup (apt.apt_callers_b ONLY)
 *
 * Lookup sequence:
 * 1) Check local Room cache first (offline-capable, instant)
 * 2) If not cached or stale (>1h), query /api/callers/lookup/{phone}
 * 3) If EXISTS in apt.apt_callers_b → return full CallerEntity from DB
 * 4) If DOES NOT EXIST → return default values:
 *    caller_name="Unknown Caller", carrier="Unknown", location="Unknown",
 *    risk_score=50, total_reports=0, is_spam=false, is_blocked=false
 * 5) Cache result in Room for future offline lookups
 *
 * IMPORTANT: Does NOT check device contacts — only apt.apt_callers_b.
 * Device contact display name is resolved separately in PopupService.
 */
public class ContactLookupService {
    private static final String TAG = "ContactLookupService";
    private static final ExecutorService executor = Executors.newCachedThreadPool();

    // Cache TTL: 1 hour for "found" results, 30 min for "not found"
    private static final long CACHE_TTL_FOUND_MS    = 60 * 60 * 1000L;
    private static final long CACHE_TTL_UNKNOWN_MS  = 30 * 60 * 1000L;

    public interface OnLookupCompleted {
        void onResult(CallerEntity caller);
        void onError(String message);
    }

    // ─────────────────────────────────────────────────────────────
    // Main lookup — non-blocking, result delivered via callback
    // ─────────────────────────────────────────────────────────────

    public static void lookup(Context context, String phoneNumber,
                              OnLookupCompleted callback) {
        executor.execute(() -> {
            try {
                // Normalise number before lookup
                String normalised = normalise(phoneNumber);
                if (normalised.isEmpty()) {
                    callback.onResult(buildDefaultCaller(phoneNumber));
                    return;
                }

                ShieldDatabase db  = ShieldDatabase.getDatabase(context);
                CallerDao      dao = db.callerDao();

                // ── 1. Local Room cache ───────────────────────────
                CallerEntity cached = dao.getByPhoneNumber(normalised);
                if (cached == null) {
                    // Also try original format
                    cached = dao.getByPhoneNumber(phoneNumber);
                }

                if (cached != null && cached.updatedAt != null) {
                    long ageMs = System.currentTimeMillis() - cached.updatedAt.getTime();
                    long ttl   = isDefaultCaller(cached) ? CACHE_TTL_UNKNOWN_MS : CACHE_TTL_FOUND_MS;
                    if (ageMs < ttl) {
                        Log.d(TAG, "📦 Cache HIT: " + cached.callerName + " for " + normalised);
                        callback.onResult(cached);
                        return;
                    }
                }

                final CallerEntity cachedFallback = cached;

                // ── 2. Remote API lookup ──────────────────────────
                lookupRemote(normalised, new OnLookupCompleted() {
                    @Override
                    public void onResult(CallerEntity remote) {
                        // Persist to Room cache
                        try {
                            remote.updatedAt = new Date();
                            dao.insertOrUpdate(remote);
                        } catch (Exception e) {
                            Log.w(TAG, "Cache write error: " + e.getMessage());
                        }
                        callback.onResult(remote);
                    }

                    @Override
                    public void onError(String message) {
                        // Remote failed — return stale cache or default
                        if (cachedFallback != null) {
                            Log.d(TAG, "📦 Stale cache fallback for: " + normalised);
                            callback.onResult(cachedFallback);
                        } else {
                            // Not in DB anywhere → return default values (Prompt 2 spec)
                            Log.d(TAG, "👤 Unknown caller: " + normalised);
                            CallerEntity def = buildDefaultCaller(normalised);
                            try {
                                def.updatedAt = new Date();
                                dao.insertOrUpdate(def);
                            } catch (Exception ignore) {}
                            callback.onResult(def);
                        }
                    }
                });

            } catch (Exception e) {
                Log.e(TAG, "❌ Lookup error: " + e.getMessage());
                callback.onError(e.getMessage());
            }
        });
    }

    // ─────────────────────────────────────────────────────────────
    // Remote API call
    // ─────────────────────────────────────────────────────────────

    private static void lookupRemote(String phoneNumber, OnLookupCompleted callback) {
        try {
            String encoded = java.net.URLEncoder.encode(phoneNumber, "UTF-8");
            URL url = new URL(Config.BACKEND_URL + "/api/callers/lookup/" + encoded);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setRequestProperty("X-API-Key", Config.API_KEY);
            conn.setConnectTimeout(5000);
            conn.setReadTimeout(5000);

            int responseCode = conn.getResponseCode();

            if (responseCode == 200) {
                // ── EXISTS in apt.apt_callers_b ───────────────────
                Scanner s = new Scanner(conn.getInputStream()).useDelimiter("\\A");
                String result = s.hasNext() ? s.next() : "";
                conn.disconnect();

                JSONObject json = new JSONObject(result);
                CallerEntity caller = new CallerEntity();
                caller.phoneNumber    = phoneNumber;
                caller.callerName     = json.optString("caller_name", "Unknown Caller");
                caller.carrier        = json.optString("carrier", "Unknown");
                caller.location       = json.optString("location", "Unknown");
                caller.riskScore      = json.optInt("risk_score", 50);
                caller.isSpam         = json.optBoolean("is_spam", false);
                caller.isBlocked      = json.optBoolean("is_blocked", false);
                caller.totalReports   = json.optInt("total_reports", 0);

                Log.d(TAG, "✅ Found: " + caller.callerName + " | Risk: " + caller.riskScore);
                callback.onResult(caller);

            } else if (responseCode == 404) {
                // ── DOES NOT EXIST in apt.apt_callers_b ──────────
                conn.disconnect();
                Log.d(TAG, "👤 Not found in apt_callers_b (404): " + phoneNumber);
                callback.onResult(buildDefaultCaller(phoneNumber));

            } else {
                conn.disconnect();
                callback.onError("HTTP " + responseCode);
            }
        } catch (Exception e) {
            callback.onError(e.getMessage());
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Helpers
    // ─────────────────────────────────────────────────────────────

    /**
     * Builds a CallerEntity with the spec-required default values for
     * numbers that DO NOT EXIST in apt.apt_callers_b.
     *
     * Per Prompt 2: caller_name="Unknown Caller", carrier="Unknown",
     * location="Unknown", risk_score=50, total_reports=0,
     * is_spam=false, is_blocked=false
     */
    public static CallerEntity buildDefaultCaller(String phoneNumber) {
        CallerEntity def = new CallerEntity();
        def.phoneNumber     = phoneNumber != null ? phoneNumber : "";
        def.callerName      = "Unknown Caller";
        def.carrier         = "Unknown";
        def.location        = "Unknown";
        def.riskScore       = 50;
        def.totalReports    = 0;
        def.isSpam          = false;
        def.isBlocked       = false;
        return def;
    }

    /** Returns true if the entity was stored as an "Unknown Caller" placeholder. */
    private static boolean isDefaultCaller(CallerEntity e) {
        return "Unknown Caller".equals(e.callerName) && e.riskScore == 50;
    }

    /** Strips spaces and dashes for consistent lookup keys. */
    private static String normalise(String number) {
        if (number == null) return "";
        return number.replaceAll("[\\s\\-()]", "");
    }
}
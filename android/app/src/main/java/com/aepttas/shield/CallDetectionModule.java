package com.aepttas.shield;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.SystemClock;
import android.provider.Settings;
import android.util.Log;

import android.Manifest;
import android.content.ContentResolver;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.provider.CallLog;
import android.provider.ContactsContract;
import androidx.core.content.ContextCompat;

import com.aepttas.shield.db.CallHistoryItem;
import com.aepttas.shield.db.ShieldDatabase;
import com.aepttas.shield.services.BlockService;
import com.aepttas.shield.services.PopupService;
import com.facebook.react.bridge.Arguments;
import com.facebook.react.bridge.Promise;
import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.bridge.ReactContextBaseJavaModule;
import com.facebook.react.bridge.ReactMethod;
import com.facebook.react.bridge.WritableArray;
import com.facebook.react.bridge.WritableMap;
import com.facebook.react.modules.core.DeviceEventManagerModule;

import org.json.JSONArray;
import org.json.JSONObject;

import java.net.HttpURLConnection;
import java.net.URL;
import java.text.SimpleDateFormat;
import java.util.List;
import java.util.Locale;
import java.util.Scanner;

public class CallDetectionModule extends ReactContextBaseJavaModule {
    private static final String TAG = "CallDetectionModule";
    private static CallDetectionModule instance;
    private static String lastCallNumber = null;
    private static String lastCallerName = null;
    private static String lastCallType   = null;
    private static long offhookTime      = 0;
    private static boolean callAnswered  = false;
    private static boolean isRinging     = false;
    private static boolean isIdleHandled = true;
    private static boolean isCallInProgress = false;

    public CallDetectionModule(ReactApplicationContext reactContext) {
        super(reactContext);
        instance = this;
    }

    public static CallDetectionModule getInstance() { return instance; }

    // ─────────────────────────────────────────────────────────────
    // Call event state machine (unchanged logic)
    // ─────────────────────────────────────────────────────────────

    public static void onCallEvent(Context context, String type,
                                   String phoneNumber, String callerName) {
        Log.d(TAG, "onCallEvent: " + type + " for " + phoneNumber);
        long duration = 0;

        if ("INCOMING".equals(type) || "OUTGOING".equals(type) || "DIALING".equals(type)) {
            lastCallNumber  = phoneNumber;
            lastCallerName  = (callerName != null && !callerName.isEmpty())
                    ? callerName : "Unknown Caller";
            lastCallType    = type;
            callAnswered    = false;
            isRinging       = "INCOMING".equals(type);
            isIdleHandled   = false;
            isCallInProgress = true;

            try {
                final Context appContext = context.getApplicationContext();
                Intent popupIntent = new Intent(appContext, PopupService.class);
                popupIntent.putExtra("phoneNumber", phoneNumber);
                popupIntent.putExtra("callerName", lastCallerName);
                popupIntent.putExtra("callType", type);
                popupIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                
                // ✅ Robust trigger: Use ApplicationContext for the delay
                new android.os.Handler(android.os.Looper.getMainLooper()).postDelayed(() -> {
                    try {
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                            appContext.startForegroundService(popupIntent);
                        } else {
                            appContext.startService(popupIntent);
                        }
                    } catch (Exception e) {
                        Log.e(TAG, "Delayed popup start failed: " + e.getMessage());
                    }
                }, 200);
            } catch (Exception e) {
                Log.e(TAG, "Popup trigger error: " + e.getMessage());
            }

        } else if ("OFFHOOK".equals(type)) {
            if (offhookTime == 0) {
                // Preserve direction: if it was OUTGOING, keep it OUTGOING. 
                // Only default to INCOMING if nothing was set.
                if (lastCallType == null) lastCallType = "INCOMING"; 
                if ("INCOMING".equals(lastCallType)) callAnswered = true;
                
                offhookTime = SystemClock.elapsedRealtime();
                isCallInProgress = true;
                Log.d(TAG, "📞 Call Answered/Started. Direction: " + lastCallType);
            }
        } else if ("IDLE".equals(type)) {
            if (isIdleHandled || !isCallInProgress) {
                Log.d(TAG, "Ignoring IDLE: No active call.");
                return;
            }

            try {
                Intent dismissIntent = new Intent(context, PopupService.class);
                dismissIntent.setAction("DISMISS_POPUP");
                context.startService(dismissIntent);
            } catch (Exception e) { /* ignore */ }

            if (offhookTime > 0) {
                duration = (SystemClock.elapsedRealtime() - offhookTime) / 1000;
            }

            if ("OUTGOING".equals(lastCallType) || "DIALING".equals(lastCallType)) {
                callAnswered = duration > 2;
            }

            Log.i(TAG, "🏁 Call Ended. Type: " + lastCallType
                    + ", Duration: " + duration + "s, Answered: " + callAnswered);

            if (instance != null) {
                instance.handleCallEnded(lastCallNumber, duration, callAnswered, lastCallType);
                instance.logCallToBackend(lastCallNumber, lastCallType, duration);
            }

            isRinging        = false;
            isIdleHandled    = true;
            isCallInProgress = false;
            offhookTime      = 0;
            lastCallType     = null;
        }

        if (instance != null) {
            WritableMap params = Arguments.createMap();
            params.putString("type", type);
            params.putString("phoneNumber",
                    phoneNumber != null ? phoneNumber
                            : (lastCallNumber != null ? lastCallNumber : ""));
            params.putString("callerName",
                    callerName != null ? callerName : lastCallerName);
            params.putDouble("duration", (double) duration);
            params.putBoolean("answered", callAnswered);
            instance.sendEvent("onCallStateChanged", params);
        }
    }

    // ─────────────────────────────────────────────────────────────
    // After-call summary popup + call logging
    // ─────────────────────────────────────────────────────────────

    private void handleCallEnded(String phoneNumber, long duration,
                                 boolean answered, String direction) {
        try {
            Context context = getReactApplicationContext();

            if (phoneNumber != null && !phoneNumber.isEmpty()) {
                Intent summaryIntent = new Intent(context, PopupService.class);
                summaryIntent.putExtra("phoneNumber", phoneNumber);
                summaryIntent.putExtra("callerName", lastCallerName);
                summaryIntent.putExtra("callType", "SUMMARY");
                summaryIntent.putExtra("duration", String.valueOf(duration));
                summaryIntent.putExtra("answered", answered);
                summaryIntent.putExtra("direction", direction);
                summaryIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    context.startForegroundService(summaryIntent);
                } else {
                    context.startService(summaryIntent);
                }
            }

            WritableMap summaryParams = Arguments.createMap();
            summaryParams.putString("phoneNumber",
                    phoneNumber != null ? phoneNumber : "");
            summaryParams.putString("callType", answered ? "answered" : "missed");
            summaryParams.putDouble("duration", (double) duration);
            sendEvent("onCallEnded", summaryParams);
        } catch (Exception e) {
            Log.e(TAG, "Error handling call end: " + e.getMessage());
        }
    }

    private void logCallToBackend(String phoneNumber, String type, long duration) {
        new Thread(() -> {
            try {
                com.aepttas.shield.db.AptCallsEntity callEntry =
                        new com.aepttas.shield.db.AptCallsEntity();
                callEntry.phoneNumber         = phoneNumber;
                callEntry.callType            = type;
                callEntry.callDurationSeconds = (int) duration;
                callEntry.callerName          = lastCallerName;

                ShieldDatabase.getDatabase(getReactApplicationContext())
                        .aptCallsDao().insert(callEntry);

                URL url = new URL(com.aepttas.shield.constants.Config.BACKEND_URL
                        + "/api/live-call/analyze");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setRequestProperty("X-API-Key",
                        com.aepttas.shield.constants.Config.API_KEY);
                conn.setDoOutput(true);

                JSONObject body = new JSONObject();
                body.put("caller_number", phoneNumber);
                body.put("caller_name", lastCallerName);
                body.put("call_type", type);
                body.put("duration", duration);
                body.put("user_id", callEntry.userId);

                try (java.io.OutputStream os = conn.getOutputStream()) {
                    os.write(body.toString().getBytes(
                            java.nio.charset.StandardCharsets.UTF_8));
                }

                if (conn.getResponseCode() == 200 || conn.getResponseCode() == 201) {
                    ShieldDatabase.getDatabase(getReactApplicationContext())
                            .aptCallsDao().markAsSynced(callEntry.callUuid);
                }
                conn.disconnect();
            } catch (Exception e) {
                Log.e(TAG, "❌ Call History Sync Error: " + e.getMessage());
            }
        }).start();
    }

    // ─────────────────────────────────────────────────────────────
    // PROMPT 9: Call History
    // ─────────────────────────────────────────────────────────────

    /**
     * Returns JSON array of call history from apt_calls_b LEFT JOIN apt_callers_b.
     * Sorted by timestamp DESC (newest first).
     * Format: [{callerName, phoneNumber, callType, duration, timestamp,
     *           riskScore, isSpam, isBlocked, carrier, location}, ...]
     */
    @ReactMethod
    public void getCallHistory(Promise promise) {
        new Thread(() -> {
            try {
                List<CallHistoryItem> items =
                        ShieldDatabase.getDatabase(getReactApplicationContext())
                                .aptCallsDao().getAllHistoryWithCallerInfo();

                WritableArray result = Arguments.createArray();
                SimpleDateFormat sdf = new SimpleDateFormat(
                        "yyyy-MM-dd HH:mm:ss", Locale.US);

                for (CallHistoryItem item : items) {
                    WritableMap map = Arguments.createMap();
                    map.putString("callUuid",
                            item.callUuid != null ? item.callUuid.toString() : "");
                    map.putString("callerName",
                            item.callerName != null ? item.callerName : "Unknown Caller");
                    map.putString("phoneNumber",
                            item.phoneNumber != null ? item.phoneNumber : "");
                    map.putString("callType",
                            item.callType != null ? item.callType : "UNKNOWN");

                    // Duration formatted as MM:SS
                    int secs = item.callDurationSeconds;
                    map.putString("duration",
                            String.format(Locale.US, "%02d:%02d", secs / 60, secs % 60));
                    map.putInt("durationSeconds", secs);

                    // Timestamp
                    map.putString("timestamp",
                            item.callTimestamp != null
                                    ? sdf.format(item.callTimestamp) : "");
                    map.putDouble("timestampMs",
                            item.callTimestamp != null
                                    ? (double) item.callTimestamp.getTime() : 0);

                    // Risk & status
                    map.putInt("riskScore", item.riskScore);
                    map.putBoolean("isSpam", item.isSpam);
                    map.putBoolean("isBlocked", item.isBlocked);
                    map.putString("carrier",
                            item.carrier != null ? item.carrier : "Unknown");
                    map.putString("location",
                            item.location != null ? item.location : "Unknown");

                    result.pushMap(map);
                }

                promise.resolve(result);
            } catch (Exception e) {
                Log.e(TAG, "❌ getCallHistory error: " + e.getMessage());
                promise.reject("CALL_HISTORY_ERROR", e.getMessage());
            }
        }).start();
    }

    /** Clear all local call history */
    @ReactMethod
    public void clearCallHistory(Promise promise) {
        new Thread(() -> {
            try {
                ShieldDatabase.getDatabase(getReactApplicationContext())
                        .aptCallsDao().deleteAll();
                promise.resolve(true);
            } catch (Exception e) {
                promise.reject("CLEAR_HISTORY_ERROR", e.getMessage());
            }
        }).start();
    }

    /**
     * Reads actual contacts from device ContactsContract
     */
    @ReactMethod
    public void getDeviceContacts(Promise promise) {
        new Thread(() -> {
            try {
                Context context = getReactApplicationContext();
                if (ContextCompat.checkSelfPermission(context, Manifest.permission.READ_CONTACTS)
                        != PackageManager.PERMISSION_GRANTED) {
                    promise.resolve(Arguments.createArray());
                    return;
                }

                ContentResolver cr = context.getContentResolver();
                Cursor cursor = cr.query(
                        ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                        new String[]{
                                ContactsContract.CommonDataKinds.Phone._ID,
                                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                                ContactsContract.CommonDataKinds.Phone.NUMBER,
                                ContactsContract.CommonDataKinds.Phone.PHOTO_THUMBNAIL_URI
                        },
                        null, null,
                        ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME + " ASC"
                );

                WritableArray array = Arguments.createArray();
                if (cursor != null) {
                    java.util.HashSet<String> seen = new java.util.HashSet<>();
                    while (cursor.moveToNext()) {
                        String id = cursor.getString(0);
                        String name = cursor.getString(1);
                        String number = cursor.getString(2);
                        String thumb = cursor.getString(3);

                        if (number != null && !number.trim().isEmpty()) {
                            String clean = number.replaceAll("[^0-9+]", "");
                            String key = (name != null ? name : "") + "|" + clean;
                            if (!seen.contains(key)) {
                                seen.add(key);
                                WritableMap map = Arguments.createMap();
                                map.putString("recordID", id != null ? id : "");
                                map.putString("displayName", name != null && !name.isEmpty() ? name : "Unknown Contact");
                                map.putString("phoneNumber", number);
                                map.putString("thumbnailPath", thumb != null ? thumb : "");
                                array.pushMap(map);
                            }
                        }
                    }
                    cursor.close();
                }
                promise.resolve(array);
            } catch (Exception e) {
                Log.e(TAG, "getDeviceContacts error: " + e.getMessage());
                promise.resolve(Arguments.createArray());
            }
        }).start();
    }

    /**
     * Reads actual phone call logs from device CallLog.Calls
     */
    @ReactMethod
    public void getDeviceCallLogs(int limit, Promise promise) {
        new Thread(() -> {
            try {
                Context context = getReactApplicationContext();
                if (ContextCompat.checkSelfPermission(context, Manifest.permission.READ_CALL_LOG)
                        != PackageManager.PERMISSION_GRANTED) {
                    promise.resolve(Arguments.createArray());
                    return;
                }

                int queryLimit = (limit > 0 && limit <= 500) ? limit : 100;
                ContentResolver cr = context.getContentResolver();
                String sortOrder = CallLog.Calls.DATE + " DESC LIMIT " + queryLimit;

                Cursor cursor = cr.query(
                        CallLog.Calls.CONTENT_URI,
                        new String[]{
                                CallLog.Calls._ID,
                                CallLog.Calls.CACHED_NAME,
                                CallLog.Calls.NUMBER,
                                CallLog.Calls.TYPE,
                                CallLog.Calls.DATE,
                                CallLog.Calls.DURATION
                        },
                        null, null,
                        sortOrder
                );

                WritableArray array = Arguments.createArray();
                SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US);

                if (cursor != null) {
                    while (cursor.moveToNext()) {
                        String id = cursor.getString(0);
                        String name = cursor.getString(1);
                        String number = cursor.getString(2);
                        int type = cursor.getInt(3);
                        long dateMs = cursor.getLong(4);
                        long durationSecs = cursor.getLong(5);

                        String typeName = "INCOMING";
                        switch (type) {
                            case CallLog.Calls.INCOMING_TYPE:
                                typeName = "INCOMING";
                                break;
                            case CallLog.Calls.OUTGOING_TYPE:
                                typeName = "OUTGOING";
                                break;
                            case CallLog.Calls.MISSED_TYPE:
                                typeName = "MISSED";
                                break;
                            case CallLog.Calls.REJECTED_TYPE:
                                typeName = "REJECTED";
                                break;
                            case CallLog.Calls.BLOCKED_TYPE:
                                typeName = "BLOCKED";
                                break;
                            default:
                                typeName = "INCOMING";
                                break;
                        }

                        WritableMap map = Arguments.createMap();
                        map.putString("id", id != null ? id : "");
                        map.putString("callerName", name != null && !name.isEmpty() ? name : "Unknown Caller");
                        map.putString("phoneNumber", number != null ? number : "");
                        map.putString("callType", typeName);
                        map.putDouble("timestampMs", (double) dateMs);
                        map.putString("timestamp", sdf.format(new java.util.Date(dateMs)));
                        map.putInt("durationSeconds", (int) durationSecs);
                        map.putString("duration", String.format(Locale.US, "%02d:%02d", durationSecs / 60, durationSecs % 60));

                        boolean isBlocked = (type == CallLog.Calls.BLOCKED_TYPE || type == CallLog.Calls.REJECTED_TYPE);
                        int riskScore = isBlocked ? 85 : 0;
                        try {
                            if (number != null && !number.isEmpty()) {
                                com.aepttas.shield.db.CallerEntity entity =
                                        ShieldDatabase.getDatabase(context).callerDao().getByPhoneNumber(number);
                                if (entity != null) {
                                    isBlocked = isBlocked || entity.isBlocked;
                                    riskScore = Math.max(riskScore, entity.riskScore);
                                }
                            }
                        } catch (Exception ignore) {}

                        map.putBoolean("isBlocked", isBlocked);
                        map.putInt("riskScore", riskScore);
                        map.putBoolean("isSpam", riskScore >= 70);

                        array.pushMap(map);
                    }
                    cursor.close();
                }
                promise.resolve(array);
            } catch (Exception e) {
                Log.e(TAG, "getDeviceCallLogs error: " + e.getMessage());
                promise.resolve(Arguments.createArray());
            }
        }).start();
    }

    // ─────────────────────────────────────────────────────────────
    // PROMPT 10: Spam & Blocked Screen
    // ─────────────────────────────────────────────────────────────

    /**
     * Returns spam report list from /api/spam-log (backend apt.spam_report_log).
     * Format: [{phoneNumber, callerName, reportType, reportedAt}, ...]
     */
    @ReactMethod
    public void getSpamList(Promise promise) {
        new Thread(() -> {
            try {
                URL url = new URL(com.aepttas.shield.constants.Config.BACKEND_URL
                        + "/api/spam-log");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setRequestProperty("X-API-Key",
                        com.aepttas.shield.constants.Config.API_KEY);
                conn.setConnectTimeout(10000);
                conn.setReadTimeout(10000);

                int code = conn.getResponseCode();
                if (code == 200) {
                    Scanner s = new Scanner(conn.getInputStream()).useDelimiter("\\A");
                    String body = s.hasNext() ? s.next() : "[]";
                    conn.disconnect();

                    JSONArray arr = new JSONArray(body);
                    WritableArray result = Arguments.createArray();
                    for (int i = 0; i < arr.length(); i++) {
                        JSONObject obj = arr.getJSONObject(i);
                        WritableMap map = Arguments.createMap();
                        map.putString("phoneNumber",
                                obj.optString("phone_number", ""));
                        map.putString("callerName",
                                obj.optString("caller_name", "Unknown"));
                        map.putString("reportType",
                                obj.optString("report_type", "Spam"));
                        map.putString("reportedAt",
                                obj.optString("reported_at", ""));
                        map.putString("reportedBy",
                                obj.optString("reported_by", ""));
                        result.pushMap(map);
                    }
                    promise.resolve(result);
                } else {
                    conn.disconnect();
                    promise.reject("SPAM_LIST_ERROR", "HTTP " + code);
                }
            } catch (Exception e) {
                Log.e(TAG, "❌ getSpamList error: " + e.getMessage());
                promise.reject("SPAM_LIST_ERROR", e.getMessage());
            }
        }).start();
    }

    /**
     * Returns blocked number list from /api/blocked (backend apt.apt_blocked_numbers).
     * Format: [{phoneNumber, callerName, blockReason, blockDate}, ...]
     */
    @ReactMethod
    public void getBlockedList(Promise promise) {
        new Thread(() -> {
            try {
                URL url = new URL(com.aepttas.shield.constants.Config.BACKEND_URL
                        + "/api/blocked");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setRequestProperty("X-API-Key",
                        com.aepttas.shield.constants.Config.API_KEY);
                conn.setConnectTimeout(10000);
                conn.setReadTimeout(10000);

                int code = conn.getResponseCode();
                if (code == 200) {
                    Scanner s = new Scanner(conn.getInputStream()).useDelimiter("\\A");
                    String body = s.hasNext() ? s.next() : "[]";
                    conn.disconnect();

                    JSONArray arr = new JSONArray(body);
                    WritableArray result = Arguments.createArray();
                    for (int i = 0; i < arr.length(); i++) {
                        JSONObject obj = arr.getJSONObject(i);
                        WritableMap map = Arguments.createMap();
                        map.putString("phoneNumber",
                                obj.optString("phone_number", ""));
                        map.putString("callerName",
                                obj.optString("caller_name", "Unknown"));
                        map.putString("blockReason",
                                obj.optString("block_reason", "User blocked"));
                        map.putString("blockDate",
                                obj.optString("block_date", ""));
                        result.pushMap(map);
                    }
                    promise.resolve(result);
                } else {
                    conn.disconnect();
                    promise.reject("BLOCKED_LIST_ERROR", "HTTP " + code);
                }
            } catch (Exception e) {
                Log.e(TAG, "❌ getBlockedList error: " + e.getMessage());
                promise.reject("BLOCKED_LIST_ERROR", e.getMessage());
            }
        }).start();
    }

    /**
     * PROMPT 10: Unblock a number.
     * Calls DELETE /api/blocked/{phone} and updates local Room cache.
     */
    @ReactMethod
    public void unblockNumber(String phoneNumber, Promise promise) {
        new Thread(() -> {
            try {
                String encoded = java.net.URLEncoder.encode(phoneNumber, "UTF-8");
                URL url = new URL(com.aepttas.shield.constants.Config.BACKEND_URL
                        + "/api/blocked/" + encoded);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("DELETE");
                conn.setRequestProperty("X-API-Key",
                        com.aepttas.shield.constants.Config.API_KEY);
                conn.setConnectTimeout(10000);
                int code = conn.getResponseCode();
                conn.disconnect();

                // Update local Room cache
                com.aepttas.shield.db.CallerDao dao =
                        ShieldDatabase.getDatabase(getReactApplicationContext()).callerDao();
                com.aepttas.shield.db.CallerEntity entity = dao.getByPhoneNumber(phoneNumber);
                if (entity != null) {
                    entity.isBlocked = false;
                    entity.updatedAt = new java.util.Date();
                    dao.update(entity);
                }
                ShieldDatabase.getDatabase(getReactApplicationContext()).blockedNumberDao()
                        .deleteByPhoneNumber(phoneNumber);

                promise.resolve(code == 200 || code == 204);
            } catch (Exception e) {
                Log.e(TAG, "❌ unblockNumber error: " + e.getMessage());
                promise.reject("UNBLOCK_ERROR", e.getMessage());
            }
        }).start();
    }

    /**
     * PROMPT 10: Delete a spam report by phone number.
     * Calls DELETE /api/spam-log/{phone}
     */
    @ReactMethod
    public void deleteSpamReport(String phoneNumber, Promise promise) {
        new Thread(() -> {
            try {
                String encoded = java.net.URLEncoder.encode(phoneNumber, "UTF-8");
                URL url = new URL(com.aepttas.shield.constants.Config.BACKEND_URL
                        + "/api/spam-log/" + encoded);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("DELETE");
                conn.setRequestProperty("X-API-Key",
                        com.aepttas.shield.constants.Config.API_KEY);
                conn.setConnectTimeout(10000);
                int code = conn.getResponseCode();
                conn.disconnect();
                ShieldDatabase.getDatabase(getReactApplicationContext()).spamReportDao()
                        .deleteByPhoneNumber(phoneNumber);
                promise.resolve(code == 200 || code == 204);
            } catch (Exception e) {
                Log.e(TAG, "❌ deleteSpamReport error: " + e.getMessage());
                promise.reject("DELETE_SPAM_ERROR", e.getMessage());
            }
        }).start();
    }

    // ─────────────────────────────────────────────────────────────
    // Existing React methods (unchanged)
    // ─────────────────────────────────────────────────────────────

    @Override
    public String getName() { return "CallDetectionModule"; }

    @ReactMethod
    public void requestRole(Promise promise) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            android.app.role.RoleManager roleManager =
                    (android.app.role.RoleManager) getReactApplicationContext()
                            .getSystemService(android.content.Context.ROLE_SERVICE);
            if (roleManager != null
                    && roleManager.isRoleAvailable(
                            android.app.role.RoleManager.ROLE_CALL_SCREENING)) {
                if (roleManager.isRoleHeld(
                        android.app.role.RoleManager.ROLE_CALL_SCREENING)) {
                    promise.resolve(true);
                } else {
                    Intent intent = roleManager.createRequestRoleIntent(
                            android.app.role.RoleManager.ROLE_CALL_SCREENING);
                    android.app.Activity activity =
                            getReactApplicationContext().getCurrentActivity();
                    if (activity != null) {
                        activity.startActivityForResult(intent, 123);
                        promise.resolve(false);
                    } else {
                        promise.resolve(false);
                    }
                }
            } else {
                promise.resolve(true);
            }
        } else {
            promise.resolve(true);
        }
    }

    @ReactMethod
    public void initialize(Promise promise) { promise.resolve(true); }

    @ReactMethod
    public void startDetection() { Log.d(TAG, "✅ startDetection"); }

    @ReactMethod
    public void stopDetection() { Log.d(TAG, "🛑 stopDetection"); }

    @ReactMethod
    public void startCallDetection(Promise promise) { promise.resolve(true); }

    @ReactMethod
    public void stopPopupService() {
        try {
            Context ctx = getReactApplicationContext();
            ctx.stopService(new Intent(ctx, PopupService.class));
        } catch (Exception e) {
            Log.e(TAG, "Error stopping PopupService: " + e.getMessage());
        }
    }

    @ReactMethod
    public void startForegroundService(Promise promise) { promise.resolve(null); }

    @ReactMethod
    public void checkOverlayPermission(Promise promise) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            promise.resolve(Settings.canDrawOverlays(getReactApplicationContext()));
        } else {
            promise.resolve(true);
        }
    }

    @ReactMethod
    public void requestOverlayPermission(Promise promise) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            Intent intent = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse("package:" + getReactApplicationContext().getPackageName()));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            getReactApplicationContext().startActivity(intent);
        }
        promise.resolve(null);
    }

    @ReactMethod
    public void requestPermissions(Promise promise) { promise.resolve(true); }

    @ReactMethod
    public void getCallState(Promise promise) {
        WritableMap map = Arguments.createMap();
        map.putInt("state", 0);
        map.putString("stateName", "IDLE");
        map.putBoolean("isActive", false);
        promise.resolve(map);
    }

    @ReactMethod
    public void isCallActive(Promise promise) { promise.resolve(false); }

    @ReactMethod
    public void blockNumber(String phoneNumber) {
        Log.d(TAG, "🚫 blockNumber: " + phoneNumber);
        BlockService.blockNumber(getReactApplicationContext(), phoneNumber, "Unknown");
    }

    @ReactMethod
    public void simulateCall(String phoneNumber) {
        Log.d(TAG, "📞 Simulating: " + phoneNumber);
        onCallEvent(getReactApplicationContext(), "INCOMING", phoneNumber, "Simulated");
    }

    @ReactMethod
    public void syncContacts(Promise promise) {
        new Thread(() -> {
            try {
                com.aepttas.shield.helpers.ContactSyncHelper.syncContactsSync(getReactApplicationContext());
                WritableMap res = Arguments.createMap();
                res.putBoolean("success", true);
                res.putString("message", "Contacts synchronized successfully with backend");
                promise.resolve(res);
            } catch (Exception e) {
                Log.e(TAG, "syncContacts error: " + e.getMessage());
                promise.reject("SYNC_ERROR", e.getMessage());
            }
        }).start();
    }

    @ReactMethod
    public void analyzeCaller(String phoneNumber, Promise promise) {
        new Thread(() -> {
            try {
                Context ctx = getReactApplicationContext();
                boolean inContacts = com.aepttas.shield.helpers.ContactUtils.isNumberInContacts(ctx, phoneNumber);
                com.aepttas.shield.db.CallerEntity caller = null;
                try {
                    caller = com.aepttas.shield.db.ShieldDatabase.getDatabase(ctx).callerDao().getByPhoneNumber(phoneNumber);
                } catch (Exception ignore) {}

                com.aepttas.shield.services.TriLayerDetectionEngine.DetectionResult res =
                        com.aepttas.shield.services.TriLayerDetectionEngine.analyze(ctx, phoneNumber, caller, inContacts);

                WritableMap map = Arguments.createMap();
                map.putInt("riskScore", res.finalRiskScore);
                map.putString("riskLevel", res.riskLevel);
                map.putBoolean("shouldAutoBlock", res.shouldAutoBlock);
                map.putBoolean("isSpoofedOrBot", res.isSpoofedOrBot);
                map.putString("digitalDnaPattern", res.digitalDnaPattern);
                map.putInt("crowdsourcedReports", res.crowdsourcedReports);
                map.putString("contextualReason", res.contextualReason);
                map.putString("recommendedAction", res.recommendedAction);
                map.putBoolean("isInContacts", inContacts);

                promise.resolve(map);
            } catch (Exception e) {
                Log.e(TAG, "analyzeCaller error: " + e.getMessage());
                promise.reject("ANALYZE_ERROR", e.getMessage());
            }
        }).start();
    }

    @ReactMethod
    public void checkAndAutoBlock(String phoneNumber, Promise promise) {
        new Thread(() -> {
            try {
                Context ctx = getReactApplicationContext();
                boolean inContacts = com.aepttas.shield.helpers.ContactUtils.isNumberInContacts(ctx, phoneNumber);
                com.aepttas.shield.db.CallerEntity caller = null;
                try {
                    caller = com.aepttas.shield.db.ShieldDatabase.getDatabase(ctx).callerDao().getByPhoneNumber(phoneNumber);
                } catch (Exception ignore) {}

                if (caller == null) {
                    caller = com.aepttas.shield.services.ContactLookupService.buildDefaultCaller(phoneNumber);
                }

                com.aepttas.shield.services.TriLayerDetectionEngine.DetectionResult res =
                        com.aepttas.shield.services.TriLayerDetectionEngine.analyze(ctx, phoneNumber, caller, inContacts);

                if (res.shouldAutoBlock) {
                    caller.riskScore = res.finalRiskScore;
                    caller.isBlocked = true;
                    com.aepttas.shield.services.AutoBlockService.checkAndBlock(ctx, caller);
                }

                WritableMap map = Arguments.createMap();
                map.putBoolean("autoBlocked", res.shouldAutoBlock);
                map.putInt("riskScore", res.finalRiskScore);
                map.putString("riskLevel", res.riskLevel);
                promise.resolve(map);
            } catch (Exception e) {
                promise.reject("AUTOBLOCK_ERROR", e.getMessage());
            }
        }).start();
    }

    @ReactMethod
    public void addListener(String eventName) {}

    @ReactMethod
    public void removeListeners(int count) {}

    public void sendEvent(String eventName, WritableMap params) {
        try {
            if (getReactApplicationContext().hasActiveCatalystInstance()) {
                getReactApplicationContext()
                        .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter.class)
                        .emit(eventName, params);
            }
        } catch (Exception e) {
            Log.e(TAG, "Error emitting event: " + e.getMessage());
        }
    }
}

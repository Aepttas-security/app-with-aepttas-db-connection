package com.aepttas.shield.services;

import android.app.AlertDialog;
import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.widget.Toast;

import com.aepttas.shield.constants.Config;
import com.aepttas.shield.db.CallerDao;
import com.aepttas.shield.db.CallerEntity;
import com.aepttas.shield.db.ShieldDatabase;

import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * PROMPT 7 – Report Service
 *
 * Handles the full report flow:
 * 1) Shows report-type dialog (Spam / Scam / Fraud / Telemarketer / Harassment)
 * 2) POST /api/callers/report → increments total_reports + 1 in apt.apt_callers_b
 *    If total_reports > 10 backend sets is_spam = true automatically
 * 3) POST /api/spam-log/add → inserts into apt.spam_report_log
 * 4) POST /api/alerts     → inserts into apt.alerts
 * 5) Shows Toast "Reported as Spam"
 * 6) Calls onDismiss() to close popup
 */
public class ReportService {
    private static final String TAG = "ReportService";
    private static final ExecutorService executor = Executors.newCachedThreadPool();

    private static final String[] REPORT_TYPES = {
            "Spam", "Scam", "Fraud", "Telemarketer", "Harassment"
    };

    // ─────────────────────────────────────────────────────────────
    // Public entry point — shows the type chooser dialog, then reports
    // ─────────────────────────────────────────────────────────────

    /**
     * Shows an AlertDialog (type chooser) and triggers report on selection.
     *
     * @param context     Any Context — uses ApplicationContext for the API call
     * @param phoneNumber Number being reported
     * @param callerName  Display name of caller
     * @param onDismiss   Called after report is submitted (dismiss popup etc.)
     */
    public static void showReportDialogAndReport(Context context,
                                                 String phoneNumber,
                                                 String callerName,
                                                 Runnable onDismiss) {
        // Dialog must run on main thread
        new Handler(Looper.getMainLooper()).post(() -> {
            try {
                AlertDialog.Builder builder = new AlertDialog.Builder(context,
                        android.R.style.Theme_Material_Dialog_Alert);
                builder.setTitle("Report Number");
                builder.setMessage("Select the type of unwanted call:");
                builder.setItems(REPORT_TYPES, (dialog, which) -> {
                    String selectedType = REPORT_TYPES[which];
                    Log.d(TAG, "📌 Report type selected: " + selectedType + " for " + phoneNumber);
                    submitReport(context, phoneNumber, callerName, selectedType, onDismiss);
                });
                builder.setNegativeButton("Cancel", null);
                AlertDialog dialog = builder.create();
                // Required for WindowManager overlay context
                if (dialog.getWindow() != null) {
                    dialog.getWindow().setType(
                            android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O
                                    ? android.view.WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
                                    : android.view.WindowManager.LayoutParams.TYPE_PHONE
                    );
                }
                dialog.show();
            } catch (Exception e) {
                // Fallback — report as "Spam" if dialog fails
                Log.w(TAG, "Dialog failed (" + e.getMessage() + "), defaulting to Spam");
                submitReport(context, phoneNumber, callerName, "Spam", onDismiss);
            }
        });
    }

    /**
     * Direct report without dialog — used when report type is already known.
     */
    public static void reportNumber(Context context,
                                    String phoneNumber,
                                    String callerName,
                                    String reportType,
                                    Runnable onDismiss) {
        submitReport(context, phoneNumber, callerName, reportType, onDismiss);
    }

    // ─────────────────────────────────────────────────────────────
    // Internal submit
    // ─────────────────────────────────────────────────────────────

    private static void submitReport(Context context,
                                     String phoneNumber,
                                     String callerName,
                                     String reportType,
                                     Runnable onDismiss) {
        executor.execute(() -> {
            // STEP 1+2 ── POST /api/reports/spam  (increments total_reports)
            postSpamReport(phoneNumber, callerName, reportType);

            // STEP 3 ── POST /api/spam-log/add    (insert into spam_report_log)
            insertSpamLog(phoneNumber, callerName, reportType);
            cacheSpamReport(context, phoneNumber, callerName, reportType);

            // STEP 4 ── POST /api/alerts
            BlockService.insertAlert(phoneNumber, callerName,
                    "REPORTED", "Number reported as " + reportType);

            // STEP 5 ── Toast on main thread
            new Handler(Looper.getMainLooper()).post(() -> {
                Toast.makeText(context, "⚠️ Reported as " + reportType,
                        Toast.LENGTH_SHORT).show();
                // STEP 6 ── Dismiss popup
                if (onDismiss != null) onDismiss.run();
            });

            Log.i(TAG, "✅ Report submitted: " + reportType + " for " + phoneNumber);
        });
    }

    // ─────────────────────────────────────────────────────────────
    // API helpers
    // ─────────────────────────────────────────────────────────────

    /**
    * POST /api/callers/report
     * Backend: increments total_reports + 1 in apt.apt_callers_b.
     *          If total_reports > 10, sets is_spam = true.
     */
    private static void postSpamReport(String phoneNumber, String callerName, String reportType) {
        try {
            URL url = new URL(Config.BACKEND_URL + "/api/callers/report");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setRequestProperty("X-API-Key", Config.API_KEY);
            conn.setDoOutput(true);
            conn.setConnectTimeout(8000);
            conn.setReadTimeout(8000);

            JSONObject body = new JSONObject();
            body.put("number", phoneNumber);
            body.put("phone_number", phoneNumber);  // accept both field names
            body.put("caller_name", callerName != null ? callerName : "Unknown");
            body.put("category", reportType);
            body.put("report_type", reportType);
            body.put("comment", "Reported from Aepttas Shield Call Popup");
            body.put("timestamp", System.currentTimeMillis());

            try (OutputStream os = conn.getOutputStream()) {
                os.write(body.toString().getBytes("utf-8"));
            }

            int code = conn.getResponseCode();
            Log.d(TAG, "📤 /api/reports/spam HTTP " + code);
            conn.disconnect();
        } catch (Exception e) {
            Log.e(TAG, "❌ postSpamReport error: " + e.getMessage());
        }
    }

    /**
     * POST /api/spam-log/add
     * Inserts a record into apt.spam_report_log
     */
    private static void insertSpamLog(String phoneNumber, String callerName, String reportType) {
        try {
            URL url = new URL(Config.BACKEND_URL + "/api/spam-log/add");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setRequestProperty("X-API-Key", Config.API_KEY);
            conn.setDoOutput(true);
            conn.setConnectTimeout(8000);
            conn.setReadTimeout(8000);

            String nowIso = new java.text.SimpleDateFormat(
                    "yyyy-MM-dd'T'HH:mm:ss'Z'", java.util.Locale.US)
                    .format(new java.util.Date());

            JSONObject body = new JSONObject();
            body.put("phone_number", phoneNumber);
            body.put("caller_name", callerName != null ? callerName : "Unknown");
            body.put("report_type", reportType);
            body.put("reported_by", "shield_user");
            body.put("reported_at", nowIso);

            try (OutputStream os = conn.getOutputStream()) {
                os.write(body.toString().getBytes("utf-8"));
            }

            int code = conn.getResponseCode();
            Log.d(TAG, "📤 /api/spam-log/add HTTP " + code);
            conn.disconnect();
        } catch (Exception e) {
            Log.e(TAG, "❌ insertSpamLog error: " + e.getMessage());
        }
    }

    private static void cacheSpamReport(Context context, String phoneNumber,
                                        String callerName, String reportType) {
        try {
            com.aepttas.shield.db.SpamReportEntity report =
                    new com.aepttas.shield.db.SpamReportEntity();
            report.phoneNumber = phoneNumber;
            report.callerName = callerName != null ? callerName : "Unknown";
            report.reportType = reportType;
            report.reportedBy = "shield_user";
            ShieldDatabase.getDatabase(context).spamReportDao().insert(report);
        } catch (Exception e) {
            Log.e(TAG, "❌ Spam-report cache error: " + e.getMessage());
        }
    }
}

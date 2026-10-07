package com.aepttas.shield.services;

import android.telecom.Call;
import android.telecom.CallScreeningService;
import android.net.Uri;
import android.util.Log;
import android.os.Build;

import androidx.annotation.NonNull;

import com.aepttas.shield.CallDetectionModule;
import com.aepttas.shield.db.AptCallsEntity;
import com.aepttas.shield.db.ShieldDatabase;
import com.aepttas.shield.helpers.NotificationHelper;

import org.json.JSONObject;

/**
 * PROMPT 8 – Call Screening Service (Auto-Block from apt.apt_blocked_numbers)
 *
 * Before allowing any call through, this service:
 * 1) Gets the incoming phone number
 * 2) Checks local Room cache (CallerEntity.isBlocked) for instant offline block
 * 3) Falls back to API /api/blocked/check/{phone} for up-to-date list
 * 4) If BLOCKED:
 *    a) Rejects call via CallResponse.Builder.setDisallowCall(true)
 *    b) Inserts into apt.alerts via BlockService.insertAlert()
 *    c) Inserts into apt_calls_b with call_type = "BLOCKED"
 *    d) Shows notification that a blocked number tried to call
 *    e) Does NOT show PopupService overlay
 * 5) If NOT blocked: proceeds normally (triggers PopupService via CallDetectionModule)
 *
 * IMPORTANT: The blocked-number check runs SYNCHRONOUSLY before respondToCall()
 * to ensure the call is rejected/allowed before Android routes it to the dialer.
 */
public class ScreeningService extends CallScreeningService {
    private static final String TAG = "ScreeningService";

    public static long lastScreenedTimestamp = 0;
    public static String lastScreenedNumber  = "";

    @Override
    public void onScreenCall(@NonNull Call.Details callDetails) {
        Uri handle = callDetails.getHandle();
        String phoneNumber = handle != null ? handle.getSchemeSpecificPart() : null;

        if (phoneNumber == null || phoneNumber.isEmpty()) {
            respondToCall(callDetails, new CallResponse.Builder().build());
            return;
        }

        // ── Extract CNAP (Network-Provided Name) ────────────────
        String cnapName = "";
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            String cn = callDetails.getCallerDisplayName();
            if (cn != null) cnapName = cn;
        }

        Log.d(TAG, "📞 Incoming call: " + phoneNumber + " | CNAP: " + cnapName);

        lastScreenedNumber    = phoneNumber;
        lastScreenedTimestamp = System.currentTimeMillis();

        // ── PROMPT 8: Blocked-number check BEFORE allowing call ─
        // BlockService.isBlocked() checks local Room cache first (fast),
        // then falls back to /api/blocked/check/{phone}.
        // Must run on current thread (ScreeningService is already on a background thread).
        boolean blocked = BlockService.isBlocked(this, phoneNumber);

        if (!blocked) {
            boolean inContacts = com.aepttas.shield.helpers.ContactUtils.isNumberInContacts(this, phoneNumber);
            com.aepttas.shield.db.CallerEntity caller = null;
            try {
                caller = ShieldDatabase.getDatabase(this).callerDao().getByPhoneNumber(phoneNumber);
            } catch (Exception ignore) {}

            TriLayerDetectionEngine.DetectionResult analysis =
                    TriLayerDetectionEngine.analyze(this, phoneNumber, caller, inContacts);

            if (analysis.shouldAutoBlock) {
                Log.w(TAG, "🚨 Tri-Layer Auto-Blocking: " + phoneNumber + " (" + analysis.digitalDnaPattern + ")");
                blocked = true;
                if (caller == null) {
                    caller = ContactLookupService.buildDefaultCaller(phoneNumber);
                }
                caller.riskScore = analysis.finalRiskScore;
                caller.isBlocked = true;
                AutoBlockService.checkAndBlock(this, caller);
            }
        }

        if (blocked) {
            Log.w(TAG, "🚫 BLOCKED call from: " + phoneNumber + " – rejecting");

            // a) Reject the call
            respondToCall(callDetails,
                    new CallResponse.Builder()
                            .setDisallowCall(true)
                            .setRejectCall(true)
                            .build());

            // b) Insert into apt.alerts (run async – call already rejected)
            new Thread(() -> {
                BlockService.insertAlert(phoneNumber, "Blocked Number",
                        "BLOCKED_CALL",
                        "Blocked number attempted to call");

                // c) Log to local apt_calls_b with call_type = "BLOCKED"
                try {
                    AptCallsEntity blockedCall = new AptCallsEntity();
                    blockedCall.phoneNumber       = phoneNumber;
                    blockedCall.callerName        = "Blocked Number";
                    blockedCall.callType          = "BLOCKED";
                    blockedCall.callDurationSeconds = 0;
                    blockedCall.isSynced          = false;
                    ShieldDatabase.getDatabase(this).aptCallsDao().insert(blockedCall);
                } catch (Exception e) {
                    Log.e(TAG, "❌ DB insert blocked call: " + e.getMessage());
                }

                // d) Show notification
                try {
                    JSONObject info = new JSONObject();
                    info.put("callerName", "Blocked Number");
                    info.put("address", phoneNumber);
                    NotificationHelper.showBlockedCallNotification(this, info, phoneNumber);
                } catch (Exception e) {
                    Log.e(TAG, "❌ Notification error: " + e.getMessage());
                }
            }).start();

            // e) Do NOT show popup for blocked calls — return here
            return;
        }

        // ── NOT blocked: trigger PopupService + React Native event ─
        final String finalCnap = cnapName;
        CallDetectionModule.onCallEvent(this, "INCOMING", phoneNumber, finalCnap);

        // Allow the call to ring
        respondToCall(callDetails, new CallResponse.Builder().build());
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        Log.d(TAG, "🛑 ScreeningService destroyed");
    }
}

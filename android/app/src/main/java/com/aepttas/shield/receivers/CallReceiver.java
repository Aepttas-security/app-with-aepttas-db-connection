package com.aepttas.shield.receivers;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.telephony.TelephonyManager;
import android.util.Log;

import androidx.core.content.ContextCompat;

import com.aepttas.shield.CallDetectionModule;
import com.aepttas.shield.services.PopupService;
import com.aepttas.shield.services.ScreeningService;

public class CallReceiver extends BroadcastReceiver {
    private static final String TAG = "CallReceiver";
    private static boolean wasRinging = false;

    @Override
    public void onReceive(Context context, Intent intent) {
        String action = intent.getAction();

        if (Intent.ACTION_NEW_OUTGOING_CALL.equals(action)) {
            String phoneNumber = intent.getStringExtra(Intent.EXTRA_PHONE_NUMBER);
            wasRinging = false;
            CallDetectionModule.onCallEvent(context, "OUTGOING", phoneNumber, null);
        } 
        else if (TelephonyManager.ACTION_PHONE_STATE_CHANGED.equals(action)) {
            String state = intent.getStringExtra(TelephonyManager.EXTRA_STATE);
            String incomingNumber = intent.getStringExtra(TelephonyManager.EXTRA_INCOMING_NUMBER);
            
            if (TelephonyManager.EXTRA_STATE_RINGING.equals(state)) {
                wasRinging = true;
                if (incomingNumber != null) {
                    CallDetectionModule.onCallEvent(context, "INCOMING", incomingNumber, null);
                }
            } else if (TelephonyManager.EXTRA_STATE_OFFHOOK.equals(state)) {
                // Logic: If it wasn't ringing, it's an outgoing call connecting
                if (!wasRinging) {
                    Log.d(TAG, "OFFHOOK detected without RINGING - Treating as OUTGOING");
                    CallDetectionModule.onCallEvent(context, "OFFHOOK", null, null);
                } else {
                    CallDetectionModule.onCallEvent(context, "OFFHOOK", null, null);
                }
            } else if (TelephonyManager.EXTRA_STATE_IDLE.equals(state)) {
                wasRinging = false;
                CallDetectionModule.onCallEvent(context, "IDLE", null, null);
            }
        }
    }
}

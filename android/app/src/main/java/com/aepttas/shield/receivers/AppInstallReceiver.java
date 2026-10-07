package com.aepttas.shield.receivers;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.util.Log;

import com.aepttas.shield.helpers.NotificationHelper;

/**
 * Listens for new app installations (ACTION_PACKAGE_ADDED)
 * to perform automatic malware/vulnerability security checks.
 */
public class AppInstallReceiver extends BroadcastReceiver {
    private static final String TAG = "AppInstallReceiver";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || intent.getAction() == null) return;

        if (Intent.ACTION_PACKAGE_ADDED.equals(intent.getAction())) {
            Uri data = intent.getData();
            if (data != null) {
                String packageName = data.getSchemeSpecificPart();
                Log.i(TAG, "📦 New application installed: " + packageName);
                
                // Show security audit notification for newly installed app
                try {
                    NotificationHelper.showNotification(
                        context,
                        "AEPTTAS Shield Security Audit",
                        "New app installed: " + packageName + ". Running security analysis...",
                        999
                    );
                } catch (Exception e) {
                    Log.e(TAG, "Failed to send install notification: " + e.getMessage());
                }
            }
        }
    }
}

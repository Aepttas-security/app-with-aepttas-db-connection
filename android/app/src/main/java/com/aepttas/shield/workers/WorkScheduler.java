package com.aepttas.shield.workers;

import android.content.Context;
import androidx.work.Constraints;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;
import java.util.concurrent.TimeUnit;

/**
 * Schedules all periodic and one-time WorkManager tasks for Shield.
 *
 * Periodic tasks:
 *   1. ShieldAutoBlock   – Auto-block audit every 4 hours
 *   2. ShieldRiskScore   – Risk score refresh every 1 hour
 *
 * One-time tasks:
 *   3. ShieldContactUpload – One-time contact upload on install
 */
public class WorkScheduler {

    public static void schedulePeriodicTasks(Context context) {
        WorkManager workManager = WorkManager.getInstance(context);

        Constraints constraints = new Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .setRequiresBatteryNotLow(true)
                .build();

        // 1. Auto-Block Audit – every 4 hours
        PeriodicWorkRequest blockRequest =
                new PeriodicWorkRequest.Builder(AutoBlockWorker.class, 4, TimeUnit.HOURS)
                        .setConstraints(constraints)
                        .build();
        workManager.enqueueUniquePeriodicWork(
                "ShieldAutoBlock", ExistingPeriodicWorkPolicy.KEEP, blockRequest);

        // 2. Risk Score Update – every 1 hour
        PeriodicWorkRequest riskRequest =
                new PeriodicWorkRequest.Builder(RiskScoreWorker.class, 1, TimeUnit.HOURS)
                        .setConstraints(constraints)
                        .build();
        workManager.enqueueUniquePeriodicWork(
                "ShieldRiskScore", ExistingPeriodicWorkPolicy.KEEP, riskRequest);

        // 3. Contact Cloud Sync – every 12 hours
        PeriodicWorkRequest contactRequest =
                new PeriodicWorkRequest.Builder(ContactUploadWorker.class, 12, TimeUnit.HOURS)
                        .setConstraints(constraints)
                        .build();
        workManager.enqueueUniquePeriodicWork(
                "ShieldContactSync", ExistingPeriodicWorkPolicy.KEEP, contactRequest);
    }

    /**
     * PROMPT 1: Schedule a one-time contact upload immediately on app open.
     * ContactUploadWorker uses KEEP policy + 24h throttle to avoid redundant uploads.
     */
    public static void scheduleOneTimeContactUpload(Context context) {
        ContactUploadWorker.scheduleNow(context);
    }

    /**
     * PROMPT 1: Force a fresh contact upload (e.g., after contacts permission is granted).
     * Resets the 24h throttle and replaces any pending upload.
     */
    public static void forceContactUpload(Context context) {
        ContactUploadWorker.forceSchedule(context);
    }
}
package com.aepttas.shield;

import android.app.AppOpsManager;
import android.app.usage.UsageStats;
import android.app.usage.UsageStatsManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Process;
import android.provider.Settings;
import android.util.Log;

import androidx.annotation.NonNull;

import com.facebook.react.bridge.Arguments;
import com.facebook.react.bridge.Promise;
import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.bridge.ReactContextBaseJavaModule;
import com.facebook.react.bridge.ReactMethod;
import com.facebook.react.bridge.WritableArray;
import com.facebook.react.bridge.WritableMap;

import java.util.Calendar;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * UsageStatsModule
 * Native Bridge for Android PACKAGE_USAGE_STATS permission & usage aggregation.
 * Supports Android 8 through 14+, including Special App Access & restricted settings handling.
 */
public class UsageStatsModule extends ReactContextBaseJavaModule {
    private static final String TAG = "UsageStatsModule";
    private final ReactApplicationContext reactContext;

    public UsageStatsModule(ReactApplicationContext reactContext) {
        super(reactContext);
        this.reactContext = reactContext;
    }

    @NonNull
    @Override
    public String getName() {
        return "UsageStatsModule";
    }

    /**
     * Check if PACKAGE_USAGE_STATS permission is granted via AppOpsManager
     */
    @ReactMethod
    public void checkUsagePermission(Promise promise) {
        try {
            AppOpsManager appOps = (AppOpsManager) reactContext.getSystemService(Context.APP_OPS_SERVICE);
            if (appOps == null) {
                promise.resolve(false);
                return;
            }
            int mode = appOps.checkOpNoThrow(
                AppOpsManager.OPSTR_GET_USAGE_STATS,
                Process.myUid(),
                reactContext.getPackageName()
            );
            boolean granted = (mode == AppOpsManager.MODE_ALLOWED);
            Log.d(TAG, "checkUsagePermission: " + granted);
            promise.resolve(granted);
        } catch (Exception e) {
            Log.e(TAG, "Error checking usage permission: " + e.getMessage());
            promise.resolve(false);
        }
    }

    /**
     * Open Android Usage Access Settings screen for this application
     */
    @ReactMethod
    public void requestUsagePermission(Promise promise) {
        try {
            Intent intent = new Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                intent.setData(Uri.parse("package:" + reactContext.getPackageName()));
            }
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

            if (intent.resolveActivity(reactContext.getPackageManager()) != null) {
                reactContext.startActivity(intent);
            } else {
                Intent fallback = new Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS);
                fallback.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                reactContext.startActivity(fallback);
            }
            promise.resolve(true);
        } catch (Exception e) {
            try {
                Intent fallback = new Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS);
                fallback.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                reactContext.startActivity(fallback);
                promise.resolve(true);
            } catch (Exception ex) {
                Log.e(TAG, "Error launching usage access settings: " + ex.getMessage());
                promise.reject("ACTIVITY_NOT_FOUND", ex.getMessage());
            }
        }
    }

    /**
     * Query daily foreground application usage minutes per package
     * Contract Output:
     * [
     *   {
     *     "package_name": "com.roblox.client",
     *     "app_name": "Roblox",
     *     "category": "Gaming",
     *     "usage_minutes": 45
     *   }
     * ]
     */
    @ReactMethod
    public void getDailyAppUsage(Promise promise) {
        try {
            UsageStatsManager usm = (UsageStatsManager) reactContext.getSystemService(Context.USAGE_STATS_SERVICE);
            if (usm == null) {
                promise.reject("UNAVAILABLE", "UsageStatsManager service not available");
                return;
            }

            // Beginning of today (midnight)
            Calendar calendar = Calendar.getInstance();
            calendar.set(Calendar.HOUR_OF_DAY, 0);
            calendar.set(Calendar.MINUTE, 0);
            calendar.set(Calendar.SECOND, 0);
            calendar.set(Calendar.MILLISECOND, 0);
            long startTime = calendar.getTimeInMillis();
            long endTime = System.currentTimeMillis();

            List<UsageStats> statsList = usm.queryUsageStats(UsageStatsManager.INTERVAL_DAILY, startTime, endTime);
            if (statsList == null || statsList.isEmpty()) {
                statsList = usm.queryUsageStats(UsageStatsManager.INTERVAL_BEST, endTime - 86400000L, endTime);
            }

            PackageManager pm = reactContext.getPackageManager();
            Map<String, Long> aggregatedUsage = new HashMap<>();

            if (statsList != null) {
                for (UsageStats usageStats : statsList) {
                    long totalTime = usageStats.getTotalTimeInForeground();
                    if (totalTime > 0) {
                        String pkg = usageStats.getPackageName();
                        long current = aggregatedUsage.containsKey(pkg) ? aggregatedUsage.get(pkg) : 0L;
                        aggregatedUsage.put(pkg, current + totalTime);
                    }
                }
            }

            WritableArray result = Arguments.createArray();
            for (Map.Entry<String, Long> entry : aggregatedUsage.entrySet()) {
                String pkg = entry.getKey();
                long millis = entry.getValue();
                int minutes = (int) Math.round(millis / 60000.0);
                if (minutes <= 0 && millis > 5000) {
                    minutes = 1;
                }

                String appName = pkg;
                String category = "Other";

                try {
                    ApplicationInfo appInfo = pm.getApplicationInfo(pkg, 0);
                    CharSequence label = pm.getApplicationLabel(appInfo);
                    if (label != null) {
                        appName = label.toString();
                    }

                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        int cat = appInfo.category;
                        if (cat == ApplicationInfo.CATEGORY_GAME) {
                            category = "Gaming";
                        } else if (cat == ApplicationInfo.CATEGORY_AUDIO) {
                            category = "Music & Audio";
                        } else if (cat == ApplicationInfo.CATEGORY_VIDEO) {
                            category = "Entertainment";
                        } else if (cat == ApplicationInfo.CATEGORY_IMAGE) {
                            category = "Photography";
                        } else if (cat == ApplicationInfo.CATEGORY_SOCIAL) {
                            category = "Social";
                        } else if (cat == ApplicationInfo.CATEGORY_NEWS) {
                            category = "News";
                        } else if (cat == ApplicationInfo.CATEGORY_MAPS) {
                            category = "Navigation";
                        } else if (cat == ApplicationInfo.CATEGORY_PRODUCTIVITY) {
                            category = "Productivity";
                        }
                    }
                } catch (PackageManager.NameNotFoundException ignored) {}

                // Categorization fallback heuristic
                if ("Other".equals(category)) {
                    String lower = pkg.toLowerCase();
                    if (lower.contains("game") || lower.contains("roblox") || lower.contains("minecraft")
                            || lower.contains("pubg") || lower.contains("freefire") || lower.contains("candycrush")) {
                        category = "Gaming";
                    } else if (lower.contains("youtube") || lower.contains("netflix") || lower.contains("primevideo")
                            || lower.contains("hotstar") || lower.contains("twitch")) {
                        category = "Entertainment";
                    } else if (lower.contains("instagram") || lower.contains("whatsapp") || lower.contains("snapchat")
                            || lower.contains("tiktok") || lower.contains("telegram") || lower.contains("facebook")) {
                        category = "Social";
                    } else if (lower.contains("chrome") || lower.contains("browser") || lower.contains("firefox") || lower.contains("opera")) {
                        category = "Browsing";
                    }
                }

                WritableMap item = Arguments.createMap();
                item.putString("package_name", pkg);
                item.putString("app_name", appName);
                item.putString("category", category);
                item.putInt("usage_minutes", minutes);
                result.pushMap(item);
            }

            promise.resolve(result);
        } catch (Exception e) {
            Log.e(TAG, "Error querying daily app usage: " + e.getMessage());
            promise.reject("USAGE_STATS_ERROR", e.getMessage());
        }
    }
}

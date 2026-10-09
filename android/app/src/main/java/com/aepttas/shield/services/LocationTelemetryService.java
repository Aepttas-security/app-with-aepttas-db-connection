package com.aepttas.shield.services;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Bundle;
import android.os.IBinder;
import android.os.PowerManager;
import android.util.Log;

import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;

import com.aepttas.shield.R;

/**
 * LocationTelemetryService
 * Android Foreground Service for resilient background GPS telemetry.
 * Prevents termination by Android Doze mode using a partial WakeLock and foreground notification.
 */
public class LocationTelemetryService extends Service {
    private static final String TAG = "LocationTelemetrySvc";
    private static final String CHANNEL_ID = "aepttas_telemetry_channel";
    private static final int NOTIFICATION_ID = 9002;

    private LocationManager locationManager;
    private PowerManager.WakeLock wakeLock;
    private boolean isTracking = false;

    private final LocationListener locationListener = new LocationListener() {
        @Override
        public void onLocationChanged(Location location) {
            if (location != null) {
                int battery = getBatteryLevel();
                Log.d(TAG, "📍 Background GPS fix: " + location.getLatitude() + ", " + location.getLongitude() + " | Battery: " + battery + "%");
            }
        }

        @Override
        public void onStatusChanged(String provider, int status, Bundle extras) {}

        @Override
        public void onProviderEnabled(String provider) {}

        @Override
        public void onProviderDisabled(String provider) {}
    };

    public static void startService(Context context) {
        try {
            Intent intent = new Intent(context, LocationTelemetryService.class);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent);
            } else {
                context.startService(intent);
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to start LocationTelemetryService: " + e.getMessage());
        }
    }

    public static void stopService(Context context) {
        try {
            Intent intent = new Intent(context, LocationTelemetryService.class);
            context.stopService(intent);
        } catch (Exception e) {
            Log.e(TAG, "Failed to stop LocationTelemetryService: " + e.getMessage());
        }
    }

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        Notification notification = buildForegroundNotification();
        startForeground(NOTIFICATION_ID, notification);

        // Acquire partial WakeLock to stay alive through Doze Mode
        try {
            PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
            if (pm != null) {
                wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "AEPTTAS:TelemetryWakeLock");
                wakeLock.setReferenceCounted(false);
                wakeLock.acquire(12 * 60 * 60 * 1000L); // 12h maximum safety cap
            }
        } catch (Exception e) {
            Log.w(TAG, "WakeLock acquisition warning: " + e.getMessage());
        }

        startLocationTracking();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (!isTracking) {
            startLocationTracking();
        }
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        stopLocationTracking();
        if (wakeLock != null && wakeLock.isHeld()) {
            try {
                wakeLock.release();
            } catch (Exception ignored) {}
        }
        Log.d(TAG, "LocationTelemetryService destroyed.");
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void startLocationTracking() {
        locationManager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);
        if (locationManager == null) return;

        isTracking = true;
        try {
            if (locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)) {
                locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 30000L, 5f, locationListener);
            }
            if (locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) {
                locationManager.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, 30000L, 5f, locationListener);
            }
            Log.d(TAG, "🚀 Location telemetry tracking registered.");
        } catch (SecurityException se) {
            Log.e(TAG, "SecurityException requesting location updates: " + se.getMessage());
        } catch (Exception e) {
            Log.e(TAG, "Error registering location updates: " + e.getMessage());
        }
    }

    private void stopLocationTracking() {
        if (locationManager != null && locationListener != null) {
            try {
                locationManager.removeUpdates(locationListener);
            } catch (SecurityException ignored) {}
        }
        isTracking = false;
    }

    private int getBatteryLevel() {
        try {
            IntentFilter ifilter = new IntentFilter(Intent.ACTION_BATTERY_CHANGED);
            Intent batteryStatus = registerReceiver(null, ifilter);
            if (batteryStatus != null) {
                int level = batteryStatus.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
                int scale = batteryStatus.getIntExtra(BatteryManager.EXTRA_SCALE, -1);
                if (level >= 0 && scale > 0) {
                    return (int) ((level / (float) scale) * 100);
                }
            }
        } catch (Exception ignored) {}
        return 90;
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "AEPTTAS Shield Telemetry",
                NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Maintains background security telemetry and parental supervision");
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(channel);
            }
        }
    }

    private Notification buildForegroundNotification() {
        return new NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("AEPTTAS Shield Active")
            .setContentText("Parental control protection and location telemetry active")
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setOngoing(true)
            .build();
    }
}

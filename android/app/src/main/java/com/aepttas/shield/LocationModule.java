package com.aepttas.shield;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import androidx.core.content.ContextCompat;

import com.facebook.react.bridge.Arguments;
import com.facebook.react.bridge.Promise;
import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.bridge.ReactContextBaseJavaModule;
import com.facebook.react.bridge.ReactMethod;
import com.facebook.react.bridge.WritableMap;

import java.util.List;

public class LocationModule extends ReactContextBaseJavaModule {
    private static final String TAG = "LocationModule";
    private final ReactApplicationContext reactContext;

    public LocationModule(ReactApplicationContext reactContext) {
        super(reactContext);
        this.reactContext = reactContext;
    }

    @Override
    public String getName() {
        return "LocationModule";
    }

    @ReactMethod
    public void startTelemetryService(Promise promise) {
        try {
            com.aepttas.shield.services.LocationTelemetryService.startService(reactContext);
            promise.resolve(true);
        } catch (Exception e) {
            promise.reject("SERVICE_ERROR", e.getMessage());
        }
    }

    @ReactMethod
    public void stopTelemetryService(Promise promise) {
        try {
            com.aepttas.shield.services.LocationTelemetryService.stopService(reactContext);
            promise.resolve(true);
        } catch (Exception e) {
            promise.reject("SERVICE_ERROR", e.getMessage());
        }
    }

    @ReactMethod
    public void isLocationEnabled(Promise promise) {
        try {
            LocationManager lm = (LocationManager) reactContext.getSystemService(Context.LOCATION_SERVICE);
            if (lm == null) {
                promise.resolve(false);
                return;
            }
            boolean gpsEnabled = false;
            boolean networkEnabled = false;
            try {
                gpsEnabled = lm.isProviderEnabled(LocationManager.GPS_PROVIDER);
            } catch (Exception ignored) {}
            try {
                networkEnabled = lm.isProviderEnabled(LocationManager.NETWORK_PROVIDER);
            } catch (Exception ignored) {}

            promise.resolve(gpsEnabled || networkEnabled);
        } catch (Exception e) {
            promise.resolve(false);
        }
    }

    @ReactMethod
    public void getCurrentLocation(Promise promise) {
        try {
            boolean fineLocation = ContextCompat.checkSelfPermission(reactContext, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED;
            boolean coarseLocation = ContextCompat.checkSelfPermission(reactContext, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED;

            if (!fineLocation && !coarseLocation) {
                promise.reject("PERMISSION_DENIED", "Location permission is not granted");
                return;
            }

            final LocationManager lm = (LocationManager) reactContext.getSystemService(Context.LOCATION_SERVICE);
            if (lm == null) {
                promise.reject("UNAVAILABLE", "LocationManager service not available");
                return;
            }

            // 1. Check last known location first
            Location bestLocation = null;
            List<String> providers = lm.getProviders(true);
            if (providers != null) {
                for (String provider : providers) {
                    try {
                        Location l = lm.getLastKnownLocation(provider);
                        if (l == null) continue;
                        if (bestLocation == null || l.getAccuracy() < bestLocation.getAccuracy()) {
                            bestLocation = l;
                        }
                    } catch (SecurityException ignored) {}
                }
            }

            // If bestLocation is recent (within 60 seconds), return immediately
            long now = System.currentTimeMillis();
            if (bestLocation != null && (now - bestLocation.getTime()) < 60000) {
                promise.resolve(buildLocationMap(bestLocation));
                return;
            }

            // 2. Otherwise request single update with timeout
            final Location fallbackLocation = bestLocation;
            final Handler handler = new Handler(Looper.getMainLooper());
            final boolean[] resolved = {false};

            final LocationListener locationListener = new LocationListener() {
                @Override
                public void onLocationChanged(Location location) {
                    if (resolved[0]) return;
                    resolved[0] = true;
                    try {
                        lm.removeUpdates(this);
                    } catch (SecurityException ignored) {}
                    promise.resolve(buildLocationMap(location));
                }

                @Override
                public void onStatusChanged(String provider, int status, Bundle extras) {}

                @Override
                public void onProviderEnabled(String provider) {}

                @Override
                public void onProviderDisabled(String provider) {}
            };

            boolean requested = false;
            try {
                if (lm.isProviderEnabled(LocationManager.GPS_PROVIDER)) {
                    lm.requestSingleUpdate(LocationManager.GPS_PROVIDER, locationListener, Looper.getMainLooper());
                    requested = true;
                }
            } catch (Exception e) {
                Log.w(TAG, "Could not request GPS update: " + e.getMessage());
            }

            try {
                if (lm.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) {
                    lm.requestSingleUpdate(LocationManager.NETWORK_PROVIDER, locationListener, Looper.getMainLooper());
                    requested = true;
                }
            } catch (Exception e) {
                Log.w(TAG, "Could not request Network update: " + e.getMessage());
            }

            // Timeout runnable after 6 seconds
            handler.postDelayed(new Runnable() {
                @Override
                public void run() {
                    if (resolved[0]) return;
                    resolved[0] = true;
                    try {
                        lm.removeUpdates(locationListener);
                    } catch (SecurityException ignored) {}

                    if (fallbackLocation != null) {
                        promise.resolve(buildLocationMap(fallbackLocation));
                    } else {
                        promise.reject("TIMEOUT", "Timed out waiting for GPS fix");
                    }
                }
            }, 6000);

            if (!requested && fallbackLocation != null) {
                resolved[0] = true;
                promise.resolve(buildLocationMap(fallbackLocation));
            } else if (!requested) {
                promise.reject("DISABLED", "No location providers are enabled");
            }

        } catch (Exception e) {
            promise.reject("ERROR", e.getMessage());
        }
    }

    private WritableMap buildLocationMap(Location loc) {
        WritableMap map = Arguments.createMap();
        map.putDouble("latitude", loc.getLatitude());
        map.putDouble("longitude", loc.getLongitude());
        map.putDouble("accuracy", loc.hasAccuracy() ? loc.getAccuracy() : 10.0);
        map.putDouble("altitude", loc.hasAltitude() ? loc.getAltitude() : 0.0);
        map.putDouble("speed", loc.hasSpeed() ? loc.getSpeed() : 0.0);
        map.putString("provider", loc.getProvider() != null ? loc.getProvider() : "gps");
        map.putDouble("timestamp", (double) loc.getTime());

        boolean isMock = false;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            isMock = loc.isMock();
        } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN_MR2) {
            isMock = loc.isFromMockProvider();
        }
        map.putBoolean("isMock", isMock);

        return map;
    }
}

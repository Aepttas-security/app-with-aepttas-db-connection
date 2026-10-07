package com.aepttas.shield;

import com.aepttas.shield.db.CallerEntity;
import com.aepttas.shield.db.CallerRepository;
import com.aepttas.shield.helpers.ContactSyncHelper;
import com.aepttas.shield.helpers.SpamReportHelper;
import com.aepttas.shield.services.AutoBlockService;
import com.aepttas.shield.services.ContactLookupService;
import com.facebook.react.bridge.Arguments;
import com.facebook.react.bridge.Promise;
import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.bridge.ReactContextBaseJavaModule;
import com.facebook.react.bridge.ReactMethod;
import com.facebook.react.bridge.WritableArray;
import com.facebook.react.bridge.WritableMap;

import java.util.List;

public class CallerDirectoryModule extends ReactContextBaseJavaModule {
    private final CallerRepository repository;

    public CallerDirectoryModule(ReactApplicationContext reactContext) {
        super(reactContext);
        this.repository = new CallerRepository(reactContext);
    }

    @Override
    public String getName() {
        return "CallerDirectoryModule";
    }

    @ReactMethod
    public void uploadContacts(Promise promise) {
        try {
            ContactSyncHelper.syncContacts(getReactApplicationContext());
            promise.resolve("Sync Started");
        } catch (Exception e) {
            promise.reject("SYNC_ERROR", e.getMessage());
        }
    }

    @ReactMethod
    public void lookupNumber(String phoneNumber, Promise promise) {
        ContactLookupService.lookup(getReactApplicationContext(), phoneNumber, new ContactLookupService.OnLookupCompleted() {
            @Override
            public void onResult(CallerEntity caller) {
                if (caller != null) {
                    WritableMap map = Arguments.createMap();
                    map.putString("callerName", caller.callerName);
                    map.putString("phoneNumber", caller.phoneNumber);
                    map.putInt("riskScore", caller.riskScore);
                    map.putInt("totalReports", caller.totalReports);
                    map.putBoolean("isSpam", caller.isSpam);
                    map.putBoolean("isBlocked", caller.isBlocked);
                    map.putString("carrier", caller.carrier);
                    map.putString("location", caller.location);
                    promise.resolve(map);
                } else {
                    promise.resolve(null);
                }
            }

            @Override
            public void onError(String message) {
                promise.reject("LOOKUP_ERROR", message);
            }
        });
    }

    @ReactMethod
    public void reportSpam(String phone, String type, String comment, Promise promise) {
        try {
            SpamReportHelper.reportSpam(getReactApplicationContext(), phone, type, comment);
            promise.resolve(true);
        } catch (Exception e) {
            promise.reject("REPORT_ERROR", e.getMessage());
        }
    }

    @ReactMethod
    public void blockNumber(String phone, Promise promise) {
        try {
            CallerEntity entity = new CallerEntity();
            entity.phoneNumber = phone;
            entity.isBlocked = true;
            AutoBlockService.checkAndBlock(getReactApplicationContext(), entity);
            promise.resolve(true);
        } catch (Exception e) {
            promise.reject("BLOCK_ERROR", e.getMessage());
        }
    }

    @ReactMethod
    public void searchCallers(String query, Promise promise) {
        repository.searchCallers(query, results -> {
            WritableArray array = Arguments.createArray();
            for (CallerEntity caller : results) {
                WritableMap map = Arguments.createMap();
                map.putString("callerName", caller.callerName);
                map.putString("phoneNumber", caller.phoneNumber);
                map.putInt("riskScore", caller.riskScore);
                map.putBoolean("isSpam", caller.isSpam);
                map.putBoolean("isBlocked", caller.isBlocked);
                array.pushMap(map);
            }
            promise.resolve(array);
        });
    }

    @ReactMethod
    public void getAnalytics(Promise promise) {
        repository.getAnalytics(stats -> {
            WritableMap map = Arguments.createMap();
            map.putInt("totalContacts", stats.totalContacts);
            map.putInt("spamCount", stats.spamCount);
            map.putInt("blockedCount", stats.blockedCount);
            map.putDouble("avgRiskScore", stats.avgRiskScore);
            map.putInt("totalReportsSum", stats.totalReportsSum);
            promise.resolve(map);
        });
    }

    @ReactMethod
    public void getRiskScore(String phone, Promise promise) {
        ContactLookupService.lookup(getReactApplicationContext(), phone, new ContactLookupService.OnLookupCompleted() {
            @Override
            public void onResult(CallerEntity caller) {
                if (caller != null) {
                    promise.resolve(caller.riskScore);
                } else {
                    promise.resolve(50); // Default
                }
            }

            @Override
            public void onError(String message) {
                promise.reject("LOOKUP_ERROR", message);
            }
        });
    }

    @ReactMethod
    public void getCallHistory(Promise promise) {
        new Thread(() -> {
            try {
                java.util.List<com.aepttas.shield.db.AptCallsEntity> history = 
                    com.aepttas.shield.db.ShieldDatabase.getDatabase(getReactApplicationContext())
                        .aptCallsDao().getAllHistory();
                
                WritableArray array = Arguments.createArray();
                for (com.aepttas.shield.db.AptCallsEntity item : history) {
                    WritableMap map = Arguments.createMap();
                    map.putString("phoneNumber", item.phoneNumber);
                    map.putString("callerName", item.callerName);
                    map.putString("callType", item.callType);
                    map.putInt("duration", item.callDurationSeconds);
                    map.putDouble("timestamp", (double) item.callTimestamp.getTime());
                    map.putBoolean("isSynced", item.isSynced);
                    array.pushMap(map);
                }
                promise.resolve(array);
            } catch (Exception e) {
                promise.reject("HISTORY_ERROR", e.getMessage());
            }
        }).start();
    }
}

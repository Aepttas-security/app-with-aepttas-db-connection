package com.aepttas.shield;

import android.util.Log;
import com.facebook.react.ReactPackage;
import com.facebook.react.bridge.NativeModule;
import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.uimanager.ViewManager;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class CallDetectionPackage implements ReactPackage {
    @Override
    public List<NativeModule> createNativeModules(ReactApplicationContext reactContext) {
        Log.d("CallDetectionPackage", "📦 Creating Native Modules...");
        List<NativeModule> modules = new ArrayList<>();
        modules.add(new CallDetectionModule(reactContext));
        modules.add(new CallerDirectoryModule(reactContext));
        modules.add(new LocationModule(reactContext));
        return modules;
    }

    @Override
    public List<ViewManager> createViewManagers(ReactApplicationContext reactContext) {
        return Collections.emptyList();
    }
}

package com.aepttas.shield;

import android.app.Application;
import android.content.res.Configuration;
import androidx.annotation.NonNull;

import com.aepttas.shield.workers.WorkScheduler;
import com.facebook.react.PackageList;
import com.facebook.react.ReactApplication;
import com.facebook.react.ReactNativeHost;
import com.facebook.react.ReactPackage;
import com.facebook.react.defaults.DefaultNewArchitectureEntryPoint;
import com.facebook.react.defaults.DefaultReactNativeHost;
import com.facebook.soloader.SoLoader;

import java.util.List;

public class MainApplication extends Application implements ReactApplication {

  private final ReactNativeHost mReactNativeHost =
    new DefaultReactNativeHost(this) {
      @Override
      public boolean getUseDeveloperSupport() {
        return BuildConfig.DEBUG;
      }

      @Override
      protected List<ReactPackage> getPackages() {
        @SuppressWarnings("UnnecessaryLocalVariable")
        List<ReactPackage> packages = new PackageList(this).getPackages();
        android.util.Log.d("MainApplication", "📦 Registering CallDetectionPackage");
        packages.add(new CallDetectionPackage());
        return packages;
      }

      @Override
      protected String getJSMainModuleName() {
        return "index";
      }

      @Override
      protected boolean isHermesEnabled() {
        return BuildConfig.IS_HERMES_ENABLED;
      }
  };

  @Override
  public ReactNativeHost getReactNativeHost() {
    return mReactNativeHost;
  }

  @Override
  public com.facebook.react.ReactHost getReactHost() {
    return com.facebook.react.defaults.DefaultReactHost.getDefaultReactHost(getApplicationContext(), mReactNativeHost, null);
  }

  @Override
  public void onCreate() {
    super.onCreate();
    try {
      com.facebook.soloader.SoLoader.init(this, com.facebook.react.soloader.OpenSourceMergedSoMapping.INSTANCE);
    } catch (Throwable t) {
      com.facebook.soloader.SoLoader.init(this, /* native exopackage */ false);
    }
    if (BuildConfig.IS_NEW_ARCHITECTURE_ENABLED) {
      DefaultNewArchitectureEntryPoint.load();
    }

    
    // 🛡️ Schedule Shield Intelligence Tasks
    try {
      WorkScheduler.schedulePeriodicTasks(this);
    } catch (Throwable t) {
      android.util.Log.e("MainApplication", "Error scheduling WorkManager tasks: " + t.getMessage());
    }
  }

  @Override
  public void onConfigurationChanged(@NonNull Configuration newConfig) {
    super.onConfigurationChanged(newConfig);
  }
}

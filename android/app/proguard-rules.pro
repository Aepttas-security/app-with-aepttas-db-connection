# Add project specific ProGuard rules here.

# Keep Aepttas Shield native classes, Room DB, services, workers, and receivers
-keep class com.aepttas.shield.** { *; }
-dontwarn com.aepttas.shield.**

# Keep React Native NativeModules
-keepclassmembers class * extends com.facebook.react.bridge.ReactContextBaseJavaModule {
    public <methods>;
}

# Keep Gson & Room
-keep class com.google.gson.** { *; }
-keep class androidx.room.** { *; }

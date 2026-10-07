# Aepttas Shield XDR — React Native UI

> AI-Powered Mobile Security Suite  
> Built with **React Native 0.86** + **TypeScript**

---

## ⚠️ Important: Why Do I See an Old Screen?

If you see **stale/old UI** after cloning this repo, it means Metro is serving a **cached old bundle**.  
Always follow the setup steps below to get a fresh build every time.

---

## Requirements

Make sure you have these installed on your machine **before** running the project:

| Tool | Version |
|---|---|
| Node.js | >= 22.11.0 |
| JDK | 17 (recommended) |
| Android Studio | Latest |
| Android NDK | 26.1.10909125 or latest |
| CMake | 3.22.1 or latest |
| React Native CLI | via npx (no global install needed) |

> **IMPORTANT:** Make sure your Android SDK path has **NO SPACES** in it.  
> ❌ Bad: `C:\Users\John Doe\AppData\Local\Android\Sdk`  
> ✅ Good: `C:\AndroidSDK`

---

## Setup Instructions (For New Machines)

### Step 1 — Clone the repository
```bash
git clone https://github.com/Aepttas-security/ui-react-2.git
cd ui-react-2
```

### Step 2 — Install JavaScript dependencies
```bash
npm install
```
> This generates the `node_modules` folder. **Never skip this step.**

### Step 3 — Start Metro Bundler (in a separate terminal)
```bash
npm start -- --reset-cache
```
> The `--reset-cache` flag ensures you always get the **latest code** and never see stale screens.

### Step 4 — Run on Android (in a new terminal)
```bash
npm run android
```
Or open the `android/` folder in Android Studio and press the **Run** button.

### Step 5 — If you see "Unable to load script" on the emulator
Run this command to forward the Metro port to your emulator:
```bash
# Standard path
adb reverse tcp:8081 tcp:8081

# If adb is not in PATH, use full path:
C:\AndroidSDK\platform-tools\adb reverse tcp:8081 tcp:8081
```

---

## Quick Refresh (When UI changes are not visible)

If the emulator shows an old screen after you've made code changes:

```bash
# 1. Stop Metro (Ctrl+C in Metro terminal)

# 2. Clean native build
cd android && ./gradlew clean && cd ..

# 3. Restart Metro with cache reset
npm start -- --reset-cache

# 4. In a separate terminal, rebuild
npm run android
```

Or, if Metro is running, just press **R twice** on your keyboard inside the emulator to reload JavaScript.

---

## Project Structure

```
ui-react-2/
├── src/
│   ├── screens/          # All application screens
│   │   ├── LoginScreen.tsx
│   │   ├── DashboardScreen.tsx
│   │   ├── GeoTrackingScreen.tsx
│   │   ├── ParentalControlScreen.tsx
│   │   ├── MalwareAnalysisScreen.tsx
│   │   ├── CallerIntelligenceScreen.tsx
│   │   ├── VulnerabilityDetectionScreen.tsx
│   │   ├── ChildModeScreen.tsx
│   │   └── ChildLinkScreen.tsx
│   ├── components/       # Reusable components (Icon, etc.)
│   └── styles/           # Design system (theme.ts, colors)
├── android/              # Native Android project
├── App.tsx               # Root app component & navigation
└── index.js              # Entry point
```

---

## Key Features

- 🔒 **Login Screen** — Email + Phone/OTP authentication
- 📊 **Dashboard** — Subscription modal, quick action tiles
- 🌍 **Geo Tracking** — IP geolocation with lat/long coordinates
- 🛡️ **Malware Analysis** — APK scanner with direct file deletion
- 👨‍👩‍👧 **Parental Control** — Dynamic QR pairing code, child monitoring
- 📞 **Caller Intelligence** — Spam detection, call blocking
- 🔍 **Vulnerability Detection** — CVE search, CERT-In advisories
- 📱 **Child Mode** — Restricted device mode with SOS

---

## Common Errors & Fixes

| Error | Fix |
|---|---|
| `Unable to load script` | Run `adb reverse tcp:8081 tcp:8081`, then reload |
| Old/stale screen showing | Run `npm start -- --reset-cache` |
| `Error resolving plugin com.facebook.react` | Run `npm install` first, then sync Gradle |
| `CMake toolchain not found` | Move Android SDK to a path with no spaces |
| `NDK folder not found` | Install NDK via Android Studio → SDK Manager → SDK Tools |

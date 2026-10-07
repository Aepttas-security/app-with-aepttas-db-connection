package com.aepttas.shield.helpers;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.telephony.TelephonyManager;
import android.util.Log;

import androidx.core.app.ActivityCompat;

import java.util.Locale;

public class CarrierInfoHelper {
    private static final String TAG = "CarrierInfoHelper";
    private final Context context;

    public CarrierInfoHelper(Context context) {
        this.context = context;
    }

    public String getCarrierName() {
        try {
            TelephonyManager tm = (TelephonyManager) context.getSystemService(Context.TELEPHONY_SERVICE);
            if (tm == null) return "Unknown";

            String carrierName = tm.getSimOperatorName();
            if (carrierName != null && !carrierName.isEmpty() && !carrierName.equals("null")) {
                return carrierName;
            }

            carrierName = tm.getNetworkOperatorName();
            if (carrierName != null && !carrierName.isEmpty() && !carrierName.equals("null")) {
                return carrierName;
            }

            return "Unknown Carrier";
        } catch (Exception e) {
            Log.e(TAG, "Error getting carrier: " + e.getMessage());
            return "Unknown";
        }
    }

    public String getLocation() {
        try {
            TelephonyManager tm = (TelephonyManager) context.getSystemService(Context.TELEPHONY_SERVICE);
            if (tm != null) {
                String countryIso = tm.getNetworkCountryIso();
                if (countryIso != null && !countryIso.isEmpty() && !countryIso.equals("null")) {
                    return getCountryName(countryIso);
                }

                countryIso = tm.getSimCountryIso();
                if (countryIso != null && !countryIso.isEmpty() && !countryIso.equals("null")) {
                    return getCountryName(countryIso);
                }
            }
            return "Unknown Location";
        } catch (Exception e) {
            Log.e(TAG, "Error getting location: " + e.getMessage());
            return "Unknown";
        }
    }

    private String getCountryName(String isoCode) {
        if (isoCode == null || isoCode.isEmpty()) return "Unknown";

        Locale locale = new Locale("", isoCode.toUpperCase());
        String countryName = locale.getDisplayCountry();
        if (countryName != null && !countryName.isEmpty()) {
            return countryName;
        }

        switch (isoCode.toUpperCase()) {
            case "IN": return "India";
            case "US": return "United States";
            case "UK": return "United Kingdom";
            case "CA": return "Canada";
            case "AU": return "Australia";
            default: return isoCode.toUpperCase();
        }
    }
}
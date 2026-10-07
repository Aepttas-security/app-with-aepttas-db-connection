package com.aepttas.shield.helpers;

import android.content.Context;
import android.telephony.TelephonyManager;
import java.util.Arrays;
import java.util.List;

public class PrivacyPolicyManager {

    // List of ISO codes for EU/EEA countries (GDPR compliant zones)
    private static final List<String> GDPR_COUNTRIES = Arrays.asList(
        "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GB", "GR", 
        "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", 
        "SI", "SK", "IS", "LI", "NO", "CH"
    );

    public static boolean isContactSyncAllowed(Context context) {
        String countryIso = getDeviceCountryIso(context);
        
        // Disable sync for GDPR countries
        if (countryIso != null && GDPR_COUNTRIES.contains(countryIso.toUpperCase())) {
            return false;
        }
        
        // Add additional logic for other regions if necessary
        return true;
    }

    public static boolean isDataStorageAllowedGlobally(Context context) {
        String countryIso = getDeviceCountryIso(context);
        return countryIso == null || !GDPR_COUNTRIES.contains(countryIso.toUpperCase());
    }

    private static String getDeviceCountryIso(Context context) {
        TelephonyManager tm = (TelephonyManager) context.getSystemService(Context.TELEPHONY_SERVICE);
        if (tm != null) {
            String countryIso = tm.getNetworkCountryIso();
            if (countryIso == null || countryIso.isEmpty()) {
                countryIso = tm.getSimCountryIso();
            }
            return countryIso;
        }
        return null;
    }
}
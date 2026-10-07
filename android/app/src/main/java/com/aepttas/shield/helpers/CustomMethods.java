package com.aepttas.shield.helpers;

import android.content.Context;
import android.provider.Settings;
import android.util.Log;

import com.aepttas.shield.db.CallerEntity;

import java.util.Calendar;

public class CustomMethods {

    private static final String TAG = "CustomMethods";

    // ============================================
    // ✅ RISK SCORE METHODS
    // ============================================
    
    public static int calculateRiskScore(CallerEntity caller) {
        if (caller == null) return 50;
        int score = 0;
        if (caller.isSpam) score += 30;
        if (caller.phoneNumber != null) {
            if (hasRepeatingPatterns(caller.phoneNumber)) score += 25;
            if (hasSequentialPatterns(caller.phoneNumber)) score += 20;
            if (isDeclaredTelemarketingNumber(caller.phoneNumber)) score += 40;
            score += getCountryRiskWeight(caller.phoneNumber);
        }
        if (isOffHoursCall()) score += 15;
        return Math.min(score, 100);
    }

    // ✅ THIS METHOD WAS MISSING - ADD IT!
    public static int computeAdvancedRiskScore(String phoneNumber, boolean isInContacts, int reportCount) {
        if (isInContacts) return 0;
        int score = reportCount * 5;
        if (isDeclaredTelemarketingNumber(phoneNumber)) score += 40;
        if (hasRepeatingPatterns(phoneNumber)) score += 20;
        if (hasSequentialPatterns(phoneNumber)) score += 15;
        return Math.min(score, 100);
    }

    // ============================================
    // ✅ HELPER METHODS
    // ============================================

    public static String cleanPhoneNumber(String phoneNumber) {
        if (phoneNumber == null) return "";
        return phoneNumber.replaceAll("[^0-9+]", "");
    }

    public static boolean numbersMatch(String num1, String num2) {
        if (num1 == null || num2 == null) return false;
        String clean1 = cleanPhoneNumber(num1);
        String clean2 = cleanPhoneNumber(num2);
        if (clean1.equals(clean2)) return true;
        if (clean1.length() >= 10 && clean2.length() >= 10) {
            String last10_1 = clean1.substring(clean1.length() - 10);
            String last10_2 = clean2.substring(clean2.length() - 10);
            if (last10_1.equals(last10_2)) return true;
        }
        return false;
    }

    public static boolean isValidPhoneNumber(String phoneNumber) {
        if (phoneNumber == null) return false;
        String nationalNumber = phoneNumber.replaceAll("\\D", "");
        return nationalNumber.matches("\\d{7,13}");
    }

    public static String getDeviceId(Context context) {
        return Settings.Secure.getString(context.getContentResolver(), Settings.Secure.ANDROID_ID);
    }

    public static boolean isDeclaredTelemarketingNumber(String rawNumber) {
        if (rawNumber == null) return false;
        String cleaned = rawNumber.replaceAll("[\\s\\-()]", "");
        return cleaned.matches("^(\\+91)?0?140\\d{7,8}$");
    }

    public static boolean isServiceCall(String rawNumber) {
        if (rawNumber == null) return false;
        String cleaned = rawNumber.replaceAll("[\\s\\-()]", "");
        return cleaned.matches("^(\\+91)?0?160\\d{7,8}$");
    }

    public static boolean hasRepeatingPatterns(String phoneNumber) {
        if (phoneNumber == null) return false;
        String digits = phoneNumber.replaceAll("\\D", "");
        if (digits.length() < 6) return false;
        if (digits.matches(".*(\\d)\\1{3,}.*")) return true;
        return digits.matches(".*(\\d{2})\\1{2,}.*");
    }

    public static boolean hasSequentialPatterns(String phoneNumber) {
        if (phoneNumber == null) return false;
        String digits = phoneNumber.replaceAll("\\D", "");
        if (digits.length() < 5) return false;
        String sequential = "01234567890 9876543210";
        for (int i = 0; i <= digits.length() - 5; i++) {
            if (sequential.contains(digits.substring(i, i + 5))) return true;
        }
        return false;
    }

    public static boolean isOffHoursCall() {
        int hour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY);
        return (hour >= 22 || hour < 6);
    }

    public static int getCountryRiskWeight(String phoneNumber) {
        if (phoneNumber == null) return 0;
        if (phoneNumber.startsWith("+41")) return 40;
        if (phoneNumber.startsWith("+234")) return 45;
        if (phoneNumber.startsWith("+92")) return 40;
        if (phoneNumber.startsWith("+86")) return 35;
        if (phoneNumber.startsWith("+55")) return 30;
        if (phoneNumber.startsWith("+") && !phoneNumber.startsWith("+91")) return 15;
        return 0;
    }

    public static String getDetectionReason(String phoneNumber, int score) {
        if (score <= 20) return "Safe Caller";
        if (isDeclaredTelemarketingNumber(phoneNumber)) return "Verified Telemarketer (140)";
        if (phoneNumber != null && (phoneNumber.startsWith("+41") || phoneNumber.startsWith("+234"))) {
            return "High-Risk International Code";
        }
        if (hasRepeatingPatterns(phoneNumber)) return "Suspicious Number Pattern";
        if (hasSequentialPatterns(phoneNumber)) return "Auto-Generated Number Pattern";
        if (isOffHoursCall()) return "Unusual Calling Hours";
        if (score > 60) return "High Likelihood of Spam";
        return "Unknown / Potential Spam";
    }

    public static String getThreatLevel(int score) {
        if (score < 25) return "Safe";
        if (score < 50) return "Low";
        if (score < 75) return "Medium";
        if (score < 90) return "High";
        return "Critical";
    }
}

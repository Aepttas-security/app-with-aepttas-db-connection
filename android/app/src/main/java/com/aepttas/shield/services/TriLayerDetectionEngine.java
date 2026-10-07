package com.aepttas.shield.services;

import android.content.Context;
import android.util.Log;

import com.aepttas.shield.db.CallerEntity;

import java.util.regex.Pattern;

/**
 * 🛡️ AEPTTAS Shield - Tri-Layer Detection Engine
 * 
 * Layer 1: Digital DNA Pattern Matching (machine-generated, spoofed, VOIP, repetitive/sequential numbers)
 * Layer 2: Crowdsourced Spam Ratings (community reports, viral spam flags, peer ratings)
 * Layer 3: Contextual Behavior Rules (local device contacts, explicit blocklists, auto-block threshold)
 */
public class TriLayerDetectionEngine {
    private static final String TAG = "TriLayerEngine";

    // Known telemarketing blocks & high-risk spoof/Wangiri prefixes
    private static final String[] SPOOF_PREFIXES = {
        "140", "141", "160",     // India TRAI telemarketing & commercial blocks
        "+232", "+881", "+882",  // Satellite / Wangiri international fraud
        "+247", "+260", "+387",  // High-risk callback scam regions
        "1900", "0900", "0800"   // Premium rate automated dialers
    };

    // Robocall / Telemarketing name indicators
    private static final String[] BOT_KEYWORDS = {
        "bot", "robo", "loan", "insurance", "telecall", "credit", "card",
        "survey", "lottery", "casino", "promo", "scam", "spam", "fraud"
    };

    public static class DetectionResult {
        public int finalRiskScore;          // 0 to 100
        public String riskLevel;            // SAFE, LOW_RISK, SUSPICIOUS, HIGH_RISK, CRITICAL_SPAM
        public boolean shouldAutoBlock;     // true if risk >= 70 or viral spam / blocklist
        public boolean isSpoofedOrBot;      // true if matched Layer 1 Digital DNA
        public String digitalDnaPattern;    // Pattern description
        public int crowdsourcedReports;     // Layer 2 report count
        public String contextualReason;     // Layer 3 device context
        public String recommendedAction;    // ALLOW, WARN, AUTO_BLOCK

        @Override
        public String toString() {
            return "DetectionResult{score=" + finalRiskScore + ", level=" + riskLevel
                    + ", autoBlock=" + shouldAutoBlock + ", dna=" + digitalDnaPattern
                    + ", context=" + contextualReason + "}";
        }
    }

    /**
     * Executes the full Tri-Layer detection sequence on the given phone number and caller entity.
     */
    public static DetectionResult analyze(Context context, String rawNumber, CallerEntity caller, boolean isInLocalContacts) {
        DetectionResult result = new DetectionResult();
        String cleanNumber = rawNumber != null ? rawNumber.replaceAll("[^0-9+]", "") : "";

        // =========================================================================
        // LAYER 3 (PART A): Contextual Behavior Rule - Whitelist & Explicit Block
        // =========================================================================
        // If caller is in local contacts, it is trusted device context
        if (isInLocalContacts) {
            result.finalRiskScore = 5;
            result.riskLevel = "SAFE";
            result.shouldAutoBlock = false;
            result.isSpoofedOrBot = false;
            result.crowdsourcedReports = caller != null ? caller.totalReports : 0;
            result.contextualReason = "Verified in Local Device Contacts";
            result.recommendedAction = "ALLOW";
            Log.d(TAG, "🟢 Layer 3 Whitelist (In Contacts): " + cleanNumber);
            return result;
        }

        // Check if explicitly blocked in local blocklist or database
        boolean isExplicitlyBlocked = (caller != null && caller.isBlocked)
                || BlockService.isBlocked(context, cleanNumber);

        if (isExplicitlyBlocked) {
            result.finalRiskScore = 100;
            result.riskLevel = "CRITICAL_SPAM";
            result.shouldAutoBlock = true;
            result.isSpoofedOrBot = false;
            result.crowdsourcedReports = caller != null ? caller.totalReports : 0;
            result.contextualReason = "Enforcing User Block List";
            result.recommendedAction = "AUTO_BLOCK";
            Log.w(TAG, "🔴 Layer 3 Blocklist Enforced: " + cleanNumber);
            return result;
        }

        // =========================================================================
        // LAYER 1: Digital DNA Pattern Matching (Machine-Generated / Spoofed Numbers)
        // =========================================================================
        int dnaScore = 0;
        String dnaPattern = "Normal Number Format";

        String digitsOnly = cleanNumber.replaceAll("[^0-9]", "");

        // 1. Length anomalies (shortcodes < 5 digits or invalid length)
        if (digitsOnly.length() > 0 && digitsOnly.length() < 7) {
            dnaScore = Math.max(dnaScore, 85);
            dnaPattern = "Machine-Generated Shortcode (" + digitsOnly.length() + " digits)";
            result.isSpoofedOrBot = true;
        }

        // 2. Repetitive digit spoofing (e.g. 9999999999, 1111111111)
        if (digitsOnly.length() >= 7 && Pattern.compile("(\\d)\\1{4,}").matcher(digitsOnly).find()) {
            dnaScore = Math.max(dnaScore, 90);
            dnaPattern = "Repetitive Digit Spoofing Pattern";
            result.isSpoofedOrBot = true;
        }

        // 3. Sequential digits spoofing (e.g. 12345678, 98765432)
        if (digitsOnly.contains("123456") || digitsOnly.contains("234567") || digitsOnly.contains("987654")) {
            dnaScore = Math.max(dnaScore, 85);
            dnaPattern = "Sequential Digit Spoofing Pattern";
            result.isSpoofedOrBot = true;
        }

        // 4. Telemarketing / Commercial DND prefixes
        for (String prefix : SPOOF_PREFIXES) {
            if (cleanNumber.startsWith(prefix) || digitsOnly.startsWith(prefix.replace("+", ""))) {
                dnaScore = Math.max(dnaScore, 80);
                dnaPattern = "Telemarketing / High-Risk Gateway (" + prefix + ")";
                result.isSpoofedOrBot = true;
                break;
            }
        }

        // 5. Bot / Robocall keyword in caller name
        if (caller != null && caller.callerName != null) {
            String lowerName = caller.callerName.toLowerCase();
            for (String kw : BOT_KEYWORDS) {
                if (lowerName.contains(kw)) {
                    dnaScore = Math.max(dnaScore, 88);
                    dnaPattern = "Automated Dialer Keyword: " + kw;
                    result.isSpoofedOrBot = true;
                    break;
                }
            }
        }

        result.digitalDnaPattern = dnaPattern;

        // =========================================================================
        // LAYER 2: Crowdsourced Spam Ratings (Peer Reports & Community Flags)
        // =========================================================================
        int crowdsourcedScore = 0;
        int totalReports = caller != null ? caller.totalReports : 0;
        boolean isSpam = caller != null && caller.isSpam;

        if (totalReports >= 10) {
            crowdsourcedScore = 95;
        } else if (totalReports >= 5) {
            crowdsourcedScore = 80;
        } else if (totalReports >= 2) {
            crowdsourcedScore = 65;
        } else if (totalReports == 1) {
            crowdsourcedScore = 45;
        }

        if (isSpam) {
            crowdsourcedScore = Math.max(crowdsourcedScore, 75);
        }

        result.crowdsourcedReports = totalReports;

        // =========================================================================
        // LAYER 3 (PART B): Synthesis & Contextual Auto-Block Evaluation
        // =========================================================================
        // Calculate weighted composite score
        int baseRisk = (caller != null) ? caller.riskScore : 50;

        int finalScore;
        if (result.isSpoofedOrBot && crowdsourcedScore > 0) {
            // Both DNA spoof and community reports agree
            finalScore = Math.max(90, Math.max(dnaScore, crowdsourcedScore));
        } else if (result.isSpoofedOrBot) {
            finalScore = dnaScore;
        } else if (crowdsourcedScore > 0) {
            finalScore = Math.max(crowdsourcedScore, baseRisk);
        } else {
            finalScore = baseRisk;
        }

        // Cap score between 0 and 100
        finalScore = Math.min(100, Math.max(0, finalScore));
        result.finalRiskScore = finalScore;

        // Assign Risk Level
        if (finalScore >= 85) {
            result.riskLevel = "CRITICAL_SPAM";
            result.recommendedAction = "AUTO_BLOCK";
        } else if (finalScore >= 70) {
            result.riskLevel = "HIGH_RISK";
            result.recommendedAction = "AUTO_BLOCK";
        } else if (finalScore >= 40) {
            result.riskLevel = "SUSPICIOUS";
            result.recommendedAction = "WARN";
        } else if (finalScore >= 20) {
            result.riskLevel = "LOW_RISK";
            result.recommendedAction = "ALLOW";
        } else {
            result.riskLevel = "SAFE";
            result.recommendedAction = "ALLOW";
        }

        // Auto-Block Policy: Trigger automatically if score >= 70 or reports > 10
        result.shouldAutoBlock = (finalScore >= 70 || totalReports > 10);
        result.contextualReason = result.shouldAutoBlock 
                ? "Auto-Block Threshold Met (Risk >= 70%)"
                : "Standard Screening (Below Auto-Block Threshold)";

        Log.i(TAG, "🧠 Tri-Layer Analysis for " + cleanNumber + ": " + result.toString());
        return result;
    }
}

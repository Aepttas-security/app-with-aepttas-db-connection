package com.aepttas.shield.helpers;

import android.content.Context;
import android.telecom.CallScreeningService;
import android.util.Log;

import org.json.JSONException;
import org.json.JSONObject;

public class CallsControlHelper {

    private static final String TAG = "MADARA";
    private final Context context;
    private final String phoneNumber;
    private final String countryNameCode;

    public interface OnDataReceivedListener {
        void onReceived(JSONObject callerInfo);
    }

    public interface OnTaskCompletedListener {
        void onTaskCompleted(boolean isSuccessful, JSONObject callerInfo);
    }

    public CallsControlHelper(Context context, String phoneNumber, String countryNameCode) {
        this.context = context;
        this.phoneNumber = phoneNumber;
        this.countryNameCode = countryNameCode;
    }

    public void getCallerInfo(OnDataReceivedListener listener) {
        try {
            JSONObject callerInfo = new JSONObject();
            
            // ✅ Using advanced scoring engine
            int riskScore = CustomMethods.computeAdvancedRiskScore(phoneNumber, false, 0);
            String threatLevel = CustomMethods.getThreatLevel(riskScore);
            String detectionReason = CustomMethods.getDetectionReason(phoneNumber, riskScore);
            boolean isSpam = riskScore > 50;
            
            callerInfo.put("callerName", isSpam ? "Suspected Spam" : "Unknown Caller");
            callerInfo.put("phoneNumber", phoneNumber);
            callerInfo.put("isSpamCall", isSpam);
            callerInfo.put("riskScore", riskScore);
            callerInfo.put("threatLevel", threatLevel);
            callerInfo.put("detectionReason", detectionReason);
            callerInfo.put("address", "India");
            
            listener.onReceived(callerInfo);
        } catch (JSONException e) {
            Log.e(TAG, "getCallerInfo: ", e);
            listener.onReceived(null);
        }
    }

    public void blockAllSpamCalls(CallScreeningService.CallResponse.Builder response, OnTaskCompletedListener listener) {
        getCallerInfo(callerInfo -> {
            if (callerInfo != null) {
                try {
                    int riskScore = callerInfo.optInt("riskScore", 0);
                    // Automatically block if score is very high (Critical/High)
                    if (riskScore >= 80) {
                        response.setDisallowCall(true);
                        response.setRejectCall(true);
                        response.setSkipCallLog(false);
                        response.setSkipNotification(false);
                        listener.onTaskCompleted(true, callerInfo);
                    } else {
                        listener.onTaskCompleted(false, callerInfo);
                    }
                } catch (Exception e) {
                    listener.onTaskCompleted(false, null);
                }
            } else {
                listener.onTaskCompleted(false, null);
            }
        });
    }
}

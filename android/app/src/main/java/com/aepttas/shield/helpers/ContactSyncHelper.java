package com.aepttas.shield.helpers;

import android.Manifest;
import android.content.ContentResolver;
import android.content.Context;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.provider.ContactsContract;

import androidx.core.content.ContextCompat;

import com.aepttas.shield.constants.Config;
import com.google.i18n.phonenumbers.NumberParseException;
import com.google.i18n.phonenumbers.PhoneNumberUtil;
import com.google.i18n.phonenumbers.Phonenumber;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class ContactSyncHelper {
    private static final ExecutorService executor = Executors.newSingleThreadExecutor();

    private static final int BATCH_SIZE   = 50; 
    private static final int MAX_RETRIES  = 3;
    private static final long BASE_DELAY_MS = 2000L;

    private static final String DEFAULT_REGION = "IN";

    public static void syncContactsSync(Context context) {
        try {
            if (ContextCompat.checkSelfPermission(context, Manifest.permission.READ_CONTACTS)
                    != PackageManager.PERMISSION_GRANTED) {
                return;
            }

            ContentResolver resolver = context.getContentResolver();
            Cursor cursor = resolver.query(
                    ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                    new String[]{
                            ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                            ContactsContract.CommonDataKinds.Phone.NUMBER
                    },
                    null, null, null
            );

            if (cursor == null) return;

            JSONArray batch = new JSONArray();

            while (cursor.moveToNext()) {
                String name  = cursor.getString(0);
                String phone = cursor.getString(1);

                if (phone == null || phone.isEmpty()) continue;

                String e164 = formatToE164(phone, DEFAULT_REGION);

                JSONObject contact = new JSONObject();
                contact.put("caller_name",  name  != null ? name : "");
                contact.put("phone_number", e164);
                batch.put(contact);

                if (batch.length() >= BATCH_SIZE) {
                    uploadBatchWithRetry(batch);
                    batch = new JSONArray();
                }
            }
            cursor.close();

            if (batch.length() > 0) {
                uploadBatchWithRetry(batch);
            }

        } catch (Exception e) {
            // Fail silently
        }
    }

    public static void syncContacts(Context context) {
        executor.execute(() -> syncContactsSync(context));
    }

    private static String formatToE164(String rawNumber, String defaultRegion) {
        // Robust cleaning: remove all non-digits
        String clean = rawNumber.replaceAll("[^0-9]", "");
        
        // If it's a 10 digit number, assume it's local Indian and add 91
        if (clean.length() == 10) {
            return "91" + clean;
        }
        
        // Otherwise return as is (Backend handles last 10 digits anyway)
        return clean;
    }

    private static void uploadBatchWithRetry(JSONArray contacts) {
        for (int attempt = 1; attempt <= MAX_RETRIES; attempt++) {
            try {
                uploadBatch(contacts);
                return;
            } catch (Exception e) {
                if (attempt < MAX_RETRIES) {
                    try {
                        Thread.sleep(BASE_DELAY_MS * (long) Math.pow(2, attempt - 1));
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        return;
                    }
                }
            }
        }
    }

    private static void uploadBatch(JSONArray contacts) throws Exception {
        URL url = new URL(Config.BACKEND_URL + "/api/callers/upload");
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setRequestProperty("Content-Type", "application/json");
        conn.setRequestProperty("X-API-Key", Config.API_KEY);
        conn.setDoOutput(true);
        conn.setConnectTimeout(15000);
        conn.setReadTimeout(15000);

        try (OutputStream os = conn.getOutputStream()) {
            byte[] input = contacts.toString().getBytes("utf-8");
            os.write(input, 0, input.length);
        }

        int code = conn.getResponseCode();
        conn.disconnect();

        if (code < 200 || code >= 300) {
            throw new Exception("HTTP " + code);
        }
    }
}

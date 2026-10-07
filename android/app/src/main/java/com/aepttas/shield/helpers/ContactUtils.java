package com.aepttas.shield.helpers;

import android.Manifest;
import android.content.ContentResolver;
import android.content.Context;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import android.provider.ContactsContract;
import android.util.Log;

import androidx.core.content.ContextCompat;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class ContactUtils {
    private static final String TAG = "ContactUtils";
    private static final ExecutorService executorService = Executors.newSingleThreadExecutor();

    public interface OnContactNameRetrievedListener {
        void onContactNameRetrieved(String contactName);
    }

    public static void getContactNameByPhoneNumber(Context context, String phoneNumber, 
                                                    OnContactNameRetrievedListener listener) {
        executorService.execute(() -> {
            String contactName = "";

            if (phoneNumber == null || phoneNumber.isEmpty()) {
                sendResult(listener, "");
                return;
            }

            // Check permission
            if (ContextCompat.checkSelfPermission(context, Manifest.permission.READ_CONTACTS) 
                    != PackageManager.PERMISSION_GRANTED) {
                Log.w(TAG, "⚠️ Contact permission NOT granted - cannot lookup");
                sendResult(listener, "");
                return;
            }

            try {
                // Clean the number for comparison
                String cleanedNumber = phoneNumber.replaceAll("[^0-9+]", "");
                Log.d(TAG, "🔍 Looking up contact for: " + cleanedNumber);
                
                // METHOD 1: Direct PhoneLookup (Most reliable)
                Uri lookupUri = Uri.withAppendedPath(
                    ContactsContract.PhoneLookup.CONTENT_FILTER_URI,
                    Uri.encode(cleanedNumber)
                );
                String[] projection = new String[]{ 
                    ContactsContract.PhoneLookup.DISPLAY_NAME,
                    ContactsContract.PhoneLookup.NUMBER
                };
                ContentResolver resolver = context.getContentResolver();
                Cursor cursor = resolver.query(lookupUri, projection, null, null, null);

                if (cursor != null) {
                    if (cursor.moveToFirst()) {
                        contactName = cursor.getString(0);
                        Log.d(TAG, "✅ Found contact (PhoneLookup): " + contactName + " for " + cleanedNumber);
                    }
                    cursor.close();
                }

                // METHOD 2: If not found, try with last 10 digits (for Indian numbers)
                if ((contactName == null || contactName.isEmpty()) && cleanedNumber.length() >= 10) {
                    String last10 = cleanedNumber.substring(Math.max(0, cleanedNumber.length() - 10));
                    
                    String[] searchPatterns = {
                        "%" + last10,
                        "%" + cleanedNumber.substring(Math.max(0, cleanedNumber.length() - 8))
                    };
                    
                    for (String pattern : searchPatterns) {
                        if (contactName != null && !contactName.isEmpty()) break;
                        
                        Uri uri = ContactsContract.CommonDataKinds.Phone.CONTENT_URI;
                        String selection = ContactsContract.CommonDataKinds.Phone.NUMBER + " LIKE ?";
                        String[] selectionArgs = new String[]{pattern};
                        
                        Cursor fuzzyCursor = resolver.query(
                            uri, 
                            new String[]{
                                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                                ContactsContract.CommonDataKinds.Phone.NUMBER
                            }, 
                            selection, 
                            selectionArgs, 
                            null
                        );
                        
                        if (fuzzyCursor != null) {
                            if (fuzzyCursor.moveToFirst()) {
                                contactName = fuzzyCursor.getString(0);
                                Log.d(TAG, "✅ Found contact (Fuzzy match): " + contactName + " for pattern " + pattern);
                            }
                            fuzzyCursor.close();
                        }
                    }
                }

                // METHOD 3: Try without country code if phone has +91
                if ((contactName == null || contactName.isEmpty()) && cleanedNumber.startsWith("+91")) {
                    String withoutCountry = cleanedNumber.substring(3);
                    if (withoutCountry.length() >= 10) {
                        Uri uri = ContactsContract.CommonDataKinds.Phone.CONTENT_URI;
                        String selection = ContactsContract.CommonDataKinds.Phone.NUMBER + " LIKE ?";
                        String[] selectionArgs = new String[]{"%" + withoutCountry};
                        
                        Cursor countryCursor = resolver.query(
                            uri, 
                            new String[]{ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME}, 
                            selection, 
                            selectionArgs, 
                            null
                        );
                        
                        if (countryCursor != null) {
                            if (countryCursor.moveToFirst()) {
                                contactName = countryCursor.getString(0);
                                Log.d(TAG, "✅ Found contact (Without country code): " + contactName);
                            }
                            countryCursor.close();
                        }
                    }
                }

                // METHOD 4: Last resort - Search by normalized number
                if (contactName == null || contactName.isEmpty()) {
                    Uri uri = ContactsContract.CommonDataKinds.Phone.CONTENT_URI;
                    String[] projectionAll = {
                        ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                        ContactsContract.CommonDataKinds.Phone.NUMBER
                    };
                    
                    Cursor allCursor = resolver.query(uri, projectionAll, null, null, null);
                    if (allCursor != null) {
                        while (allCursor.moveToNext()) {
                            String dbNumber = allCursor.getString(1);
                            if (dbNumber != null) {
                                String cleanedDb = dbNumber.replaceAll("[^0-9+]", "");
                                if (cleanedDb.equals(cleanedNumber) || 
                                    cleanedDb.endsWith(cleanedNumber) || 
                                    cleanedNumber.endsWith(cleanedDb)) {
                                    contactName = allCursor.getString(0);
                                    Log.d(TAG, "✅ Found contact (Full scan): " + contactName);
                                    break;
                                }
                            }
                        }
                        allCursor.close();
                    }
                }

            } catch (Exception e) {
                Log.e(TAG, "❌ Error looking up contact: " + e.getMessage(), e);
            }

            // If still empty, return "Unknown"
            if (contactName == null || contactName.isEmpty()) {
                contactName = "";
            }
            
            sendResult(listener, contactName);
        });
    }

    public static boolean isNumberInContacts(Context context, String phoneNumber) {
        String name = getContactNameSync(context, phoneNumber);
        return name != null && !name.isEmpty() && !name.equals("null");
    }

    public static String getContactNameSync(Context context, String phoneNumber) {
        if (phoneNumber == null || phoneNumber.isEmpty()) return "";
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.READ_CONTACTS) 
                != PackageManager.PERMISSION_GRANTED) {
            return "";
        }
        try {
            String cleanedNumber = phoneNumber.replaceAll("[^0-9+]", "");
            Uri lookupUri = Uri.withAppendedPath(
                ContactsContract.PhoneLookup.CONTENT_FILTER_URI,
                Uri.encode(cleanedNumber)
            );
            String[] projection = new String[]{ 
                ContactsContract.PhoneLookup.DISPLAY_NAME,
                ContactsContract.PhoneLookup.NUMBER
            };
            ContentResolver resolver = context.getContentResolver();
            Cursor cursor = resolver.query(lookupUri, projection, null, null, null);
            if (cursor != null) {
                try {
                    if (cursor.moveToFirst()) {
                        return cursor.getString(0);
                    }
                } finally {
                    cursor.close();
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Error in getContactNameSync: " + e.getMessage());
        }
        return "";
    }

    private static void sendResult(OnContactNameRetrievedListener listener, String result) {
        new Handler(Looper.getMainLooper()).post(() -> listener.onContactNameRetrieved(result));
    }
}
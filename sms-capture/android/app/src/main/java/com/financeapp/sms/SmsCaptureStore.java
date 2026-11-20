package com.financeapp.sms;

import android.content.Context;
import android.content.SharedPreferences;
import java.util.HashSet;
import java.util.Set;

/**
 * App-private settings shared by the JS side (via SmsCaptureModule) and the background receiver/worker.
 * The token is the user's API token; prefer a long-lived, SMS-only device token issued by your backend.
 */
public final class SmsCaptureStore {
    private static final String PREFS = "sms_capture";
    private final SharedPreferences p;

    public SmsCaptureStore(Context context) {
        p = context.getApplicationContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    public boolean isEnabled() { return p.getBoolean("enabled", false); }
    public void setEnabled(boolean v) { p.edit().putBoolean("enabled", v).apply(); }

    public String baseUrl() { return p.getString("baseUrl", null); }
    public String token() { return p.getString("token", null); }
    public void setServer(String baseUrl, String token) {
        p.edit().putString("baseUrl", baseUrl).putString("token", token).apply();
    }

    /** Normalised sender IDs (SmsFilter.normalizeSender) the user's banks/wallets send from. */
    public Set<String> senders() { return new HashSet<>(p.getStringSet("senders", new HashSet<>())); }
    public void setSenders(Set<String> normalized) { p.edit().putStringSet("senders", new HashSet<>(normalized)).apply(); }

    /** Forget everything (user turned the feature off or signed out). */
    public void clear() { p.edit().clear().apply(); }
}

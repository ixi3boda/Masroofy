package com.financeapp.sms;

import android.content.Context;
import android.util.Log;
import androidx.work.BackoffPolicy;
import androidx.work.Constraints;
import androidx.work.Data;
import androidx.work.ExistingWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.OneTimeWorkRequest;
import androidx.work.WorkManager;
import androidx.work.Worker;
import androidx.work.WorkerParameters;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * Uploads one captured SMS to POST {baseUrl}/api/sms/ingest. WorkManager keeps the job across app restarts
 * and reboots, waits for a network connection, and retries with back-off, so no transaction is lost offline.
 * The server ignores repeats (same sender + time + text), so a retry can never count a transaction twice.
 */
public class SmsUploadWorker extends Worker {
    private static final String TAG = "SmsCapture";
    private static final int MAX_ATTEMPTS = 60;

    public SmsUploadWorker(Context context, WorkerParameters params) { super(context, params); }

    public static void enqueue(Context context, String sender, String body, long receivedAt) {
        Data input = new Data.Builder()
                .putString("sender", sender)
                .putString("body", body)
                .putLong("receivedAt", receivedAt)
                .build();
        OneTimeWorkRequest req = new OneTimeWorkRequest.Builder(SmsUploadWorker.class)
                .setInputData(input)
                .setConstraints(new Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
                .build();
        // Unique name per SMS: a second broadcast of the same SMS does not queue a second upload.
        String name = "sms-" + Integer.toHexString((sender + "|" + receivedAt + "|" + body).hashCode());
        WorkManager.getInstance(context).enqueueUniqueWork(name, ExistingWorkPolicy.KEEP, req);
    }

    @Override
    public Result doWork() {
        SmsCaptureStore store = new SmsCaptureStore(getApplicationContext());
        String baseUrl = store.baseUrl(), token = store.token();
        if (!store.isEnabled()) return Result.failure();                  // user switched the feature off
        if (baseUrl == null || token == null) return retryOrGiveUp();     // signed out: wait for the app to set a token

        HttpURLConnection con = null;
        try {
            JSONObject msg = new JSONObject();
            msg.put("sender", getInputData().getString("sender"));
            msg.put("body", getInputData().getString("body"));
            msg.put("receivedAt", getInputData().getLong("receivedAt", System.currentTimeMillis()));
            JSONObject payload = new JSONObject();
            payload.put("messages", new JSONArray().put(msg));
            byte[] bytes = payload.toString().getBytes(StandardCharsets.UTF_8);

            con = (HttpURLConnection) URI.create(trimSlash(baseUrl) + "/api/sms/ingest").toURL().openConnection();
            con.setRequestMethod("POST");
            con.setConnectTimeout(15_000);
            con.setReadTimeout(20_000);
            con.setDoOutput(true);
            con.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            con.setRequestProperty("Authorization", "Bearer " + token);
            con.setFixedLengthStreamingMode(bytes.length);
            try (OutputStream os = con.getOutputStream()) { os.write(bytes); }

            int code = con.getResponseCode();
            if (code >= 200 && code < 300) {
                String response = read(con.getInputStream());
                SmsCaptureModule.emitProcessed(response);                   // lets an open app refresh balances/drafts
                return Result.success();
            }
            Log.w(TAG, "upload failed with HTTP " + code);
            if (code == 401 || code == 403 || code == 408 || code == 429 || code >= 500) return retryOrGiveUp();
            return Result.failure();                                        // 400 etc.: this message will never be accepted
        } catch (IOException | JSONException e) {
            Log.w(TAG, "upload error: " + e.getMessage());
            return retryOrGiveUp();
        } finally {
            if (con != null) con.disconnect();
        }
    }

    private Result retryOrGiveUp() { return getRunAttemptCount() < MAX_ATTEMPTS ? Result.retry() : Result.failure(); }

    private static String trimSlash(String s) { return s.endsWith("/") ? s.substring(0, s.length() - 1) : s; }

    private static String read(InputStream in) throws IOException {
        try (InputStream is = in; ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buf = new byte[4096]; int n;
            while ((n = is.read(buf)) > 0) out.write(buf, 0, n);
            return out.toString("UTF-8");
        }
    }
}

package com.financeapp.sms;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.provider.Telephony;
import android.telephony.SmsMessage;
import android.util.Log;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * Called by Android for every incoming SMS, even when the app is closed (declared in AndroidManifest.xml).
 * Joins multi-part messages, keeps only bank/wallet senders, drops OTPs, and queues the upload.
 * It does no network work itself: onReceive must return quickly.
 */
public class SmsReceiver extends BroadcastReceiver {
    private static final String TAG = "SmsCapture";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || !Telephony.Sms.Intents.SMS_RECEIVED_ACTION.equals(intent.getAction())) return;
        SmsCaptureStore store = new SmsCaptureStore(context);
        if (!store.isEnabled()) return;
        Set<String> allow = store.senders();

        SmsMessage[] parts = Telephony.Sms.Intents.getMessagesFromIntent(intent);
        if (parts == null || parts.length == 0) return;

        // One broadcast can hold several parts of one long SMS (and, rarely, several SMS): group by sender.
        Map<String, StringBuilder> bodies = new LinkedHashMap<>();
        Map<String, Long> times = new LinkedHashMap<>();
        for (SmsMessage part : parts) {
            if (part == null) continue;
            String from = part.getDisplayOriginatingAddress();
            if (from == null) from = part.getOriginatingAddress();
            if (from == null) continue;
            String body = part.getMessageBody();
            bodies.computeIfAbsent(from, k -> new StringBuilder()).append(body == null ? "" : body);
            times.putIfAbsent(from, part.getTimestampMillis());
        }

        for (Map.Entry<String, StringBuilder> e : bodies.entrySet()) {
            String sender = e.getKey(), body = e.getValue().toString();
            if (!SmsFilter.isAllowedSender(sender, allow)) continue;      // personal SMS: ignored, never read further
            if (SmsFilter.looksLikeOtp(body)) { Log.d(TAG, "OTP from " + sender + " kept on device"); continue; }
            long ts = times.get(sender) != null && times.get(sender) > 0 ? times.get(sender) : System.currentTimeMillis();
            SmsUploadWorker.enqueue(context, sender, body, ts);
            SmsCaptureModule.emitCaptured(sender, ts);
        }
    }
}

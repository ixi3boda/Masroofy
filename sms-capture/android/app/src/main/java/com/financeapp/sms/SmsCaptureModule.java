package com.financeapp.sms;

import android.Manifest;
import android.content.pm.PackageManager;
import androidx.work.WorkManager;
import com.facebook.react.bridge.Arguments;
import com.facebook.react.bridge.Promise;
import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.bridge.ReactContextBaseJavaModule;
import com.facebook.react.bridge.ReactMethod;
import com.facebook.react.bridge.ReadableArray;
import com.facebook.react.bridge.WritableMap;
import com.facebook.react.modules.core.DeviceEventManagerModule;
import java.lang.ref.WeakReference;
import java.util.HashSet;
import java.util.Set;

/**
 * NativeModules.SmsCapture in JavaScript. JS calls configure / setSenders / setEnabled; the receiver and worker
 * run natively even when the app is closed, and emit "SmsCaptured" / "SmsProcessed" events when it is open.
 */
public class SmsCaptureModule extends ReactContextBaseJavaModule {
    public static final String NAME = "SmsCapture";
    private static WeakReference<ReactApplicationContext> active = new WeakReference<>(null);

    public SmsCaptureModule(ReactApplicationContext context) {
        super(context);
        active = new WeakReference<>(context);
    }

    @Override public String getName() { return NAME; }

    /** Server address and the user's token (call again whenever the token is refreshed). */
    @ReactMethod
    public void configure(String baseUrl, String token, Promise promise) {
        new SmsCaptureStore(getReactApplicationContext()).setServer(baseUrl, token);
        promise.resolve(true);
    }

    /** Sender IDs of the user's banks/wallets (from GET /api/sms/senders). */
    @ReactMethod
    public void setSenders(ReadableArray senderIds, Promise promise) {
        Set<String> s = new HashSet<>();
        for (int i = 0; i < senderIds.size(); i++) {
            String n = SmsFilter.normalizeSender(senderIds.getString(i));
            if (!n.isEmpty()) s.add(n);
        }
        new SmsCaptureStore(getReactApplicationContext()).setSenders(s);
        promise.resolve(s.size());
    }

    @ReactMethod
    public void setEnabled(boolean enabled, Promise promise) {
        SmsCaptureStore store = new SmsCaptureStore(getReactApplicationContext());
        if (enabled && getReactApplicationContext().checkSelfPermission(Manifest.permission.RECEIVE_SMS) != PackageManager.PERMISSION_GRANTED) {
            promise.reject("E_PERMISSION", "RECEIVE_SMS permission not granted");
            return;
        }
        store.setEnabled(enabled);
        promise.resolve(enabled);
    }

    /** Turn off and forget server, token and senders; cancel queued uploads. */
    @ReactMethod
    public void reset(Promise promise) {
        new SmsCaptureStore(getReactApplicationContext()).clear();
        WorkManager.getInstance(getReactApplicationContext()).cancelAllWork();
        promise.resolve(true);
    }

    @ReactMethod
    public void getStatus(Promise promise) {
        SmsCaptureStore store = new SmsCaptureStore(getReactApplicationContext());
        WritableMap m = Arguments.createMap();
        m.putBoolean("enabled", store.isEnabled());
        m.putBoolean("hasPermission", getReactApplicationContext().checkSelfPermission(Manifest.permission.RECEIVE_SMS) == PackageManager.PERMISSION_GRANTED);
        m.putBoolean("configured", store.baseUrl() != null && store.token() != null);
        m.putInt("senderCount", store.senders().size());
        promise.resolve(m);
    }

    // Required by NativeEventEmitter on Android.
    @ReactMethod public void addListener(String eventName) { }
    @ReactMethod public void removeListeners(double count) { }

    static void emitCaptured(String sender, long receivedAt) {
        WritableMap m = Arguments.createMap();
        m.putString("sender", sender);
        m.putDouble("receivedAt", (double) receivedAt);
        emit("SmsCaptured", m);
    }

    /** response = JSON returned by /api/sms/ingest (results with APPLIED / DRAFT / IGNORED). */
    static void emitProcessed(String response) {
        WritableMap m = Arguments.createMap();
        m.putString("response", response);
        emit("SmsProcessed", m);
    }

    private static void emit(String event, WritableMap payload) {
        ReactApplicationContext ctx = active.get();
        if (ctx == null || !ctx.hasActiveReactInstance()) return;     // app closed: data is on the server anyway
        ctx.getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter.class).emit(event, payload);
    }
}

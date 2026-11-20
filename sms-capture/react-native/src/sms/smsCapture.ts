// JS side of the Android SMS capture module (android/.../sms/SmsCaptureModule.java).
import { NativeEventEmitter, NativeModules, PermissionsAndroid, Platform } from 'react-native';
import type { IngestResult, SmsApi } from './smsApi';

export interface SmsCaptureStatus {
  enabled: boolean;
  hasPermission: boolean;
  configured: boolean;
  senderCount: number;
}

interface NativeSmsCapture {
  configure(baseUrl: string, token: string): Promise<boolean>;
  setSenders(senderIds: string[]): Promise<number>;
  setEnabled(enabled: boolean): Promise<boolean>;
  reset(): Promise<boolean>;
  getStatus(): Promise<SmsCaptureStatus>;
}

const Native: NativeSmsCapture | undefined =
  Platform.OS === 'android' ? (NativeModules.SmsCapture as NativeSmsCapture | undefined) : undefined;

export const isSmsCaptureSupported = (): boolean => Native !== undefined;

export type EnableResult = 'enabled' | 'unsupported' | 'denied' | 'blocked';

/**
 * Show your own explanation screen first (what is read, what is uploaded, how to turn it off),
 * then call this. Asks for RECEIVE_SMS, stores server + token, loads the bank/wallet allow-list, turns capture on.
 */
export async function enableSmsCapture(
  api: SmsApi,
  server: { baseUrl: string; token: string },
  rationale: { title: string; message: string; ok: string },
): Promise<EnableResult> {
  if (!Native) return 'unsupported';
  const r = await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.RECEIVE_SMS, {
    title: rationale.title,
    message: rationale.message,
    buttonPositive: rationale.ok,
  });
  if (r === PermissionsAndroid.RESULTS.NEVER_ASK_AGAIN) return 'blocked'; // user must allow it in system settings
  if (r !== PermissionsAndroid.RESULTS.GRANTED) return 'denied';

  await Native.configure(server.baseUrl, server.token);
  await refreshSmsSenders(api);
  await Native.setEnabled(true);
  return 'enabled';
}

/** Call after the user adds a bank/wallet sender, and on app start. */
export async function refreshSmsSenders(api: SmsApi): Promise<number> {
  if (!Native) return 0;
  const senders = await api.getSenders();
  return Native.setSenders(senders.filter((s) => s.enabled).map((s) => s.senderId));
}

/** Call whenever your auth token is refreshed, so background uploads keep working. */
export async function updateSmsCaptureToken(baseUrl: string, token: string): Promise<void> {
  if (Native) await Native.configure(baseUrl, token);
}

/** Turn off and forget token/senders on this phone (e.g. on sign-out). */
export async function disableSmsCapture(): Promise<void> {
  if (Native) await Native.reset();
}

export async function getSmsCaptureStatus(): Promise<SmsCaptureStatus | null> {
  return Native ? Native.getStatus() : null;
}

/**
 * Events while the app is open: "captured" when a bank SMS arrives, "processed" when the server has
 * applied it (refresh balances) or created a draft (show the review badge).
 */
export function onSmsEvents(handlers: {
  captured?: (e: { sender: string; receivedAt: number }) => void;
  processed?: (results: IngestResult[]) => void;
}): () => void {
  if (!Native) return () => undefined;
  const emitter = new NativeEventEmitter(NativeModules.SmsCapture);
  const subs = [
    emitter.addListener('SmsCaptured', (e: { sender: string; receivedAt: number }) => handlers.captured?.(e)),
    emitter.addListener('SmsProcessed', (e: { response: string }) => {
      try {
        handlers.processed?.((JSON.parse(e.response) as { results: IngestResult[] }).results);
      } catch {
        /* ignore malformed payloads */
      }
    }),
  ];
  return () => subs.forEach((s) => s.remove());
}

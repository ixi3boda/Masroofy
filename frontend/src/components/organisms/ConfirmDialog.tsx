import React, { ReactNode } from 'react';
import { Modal, Pressable, StyleSheet, View } from 'react-native';
import { colors, radii, shadows } from '@theme/index';
import AppText from '@components/atoms/Text';
import { strings } from '@/strings';

export interface ConfirmDialogProps {
  visible: boolean;
  title: string;
  message: string;
  /** Stacked buttons, e.g. a danger "Delete" + outline "Keep transaction". */
  actions: ReactNode;
  /** Scrim tap and Android back button — treat as "cancel". */
  onDismiss: () => void;
}

/** Centered confirmation modal for destructive or unsaved-changes decisions. */
const ConfirmDialog: React.FC<ConfirmDialogProps> = ({ visible, title, message, actions, onDismiss }) => (
  <Modal
    visible={visible}
    transparent
    animationType="fade"
    statusBarTranslucent
    onRequestClose={onDismiss}
  >
    <View style={styles.backdrop}>
      <Pressable style={StyleSheet.absoluteFill} onPress={onDismiss} accessibilityLabel={strings.common.a11y.dismiss} />
      <View style={styles.dialog} accessibilityViewIsModal accessibilityRole="alert">
        <AppText variant="subheading18">{title}</AppText>
        <AppText variant="body14">{message}</AppText>
        <View style={styles.actions}>{actions}</View>
      </View>
    </View>
  </Modal>
);

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    justifyContent: 'center',
    padding: 24,
    backgroundColor: colors.overlay.scrim,
  },
  dialog: {
    gap: 12,
    padding: 24,
    borderRadius: radii.xxl,
    backgroundColor: colors.surface,
    ...shadows.card,
  },
  actions: { gap: 12, marginTop: 8 },
});

export default ConfirmDialog;

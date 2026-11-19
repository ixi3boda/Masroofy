import React, { ReactNode } from 'react';
import {
  Modal,
  View,
  TouchableOpacity,
  StyleSheet,
  ViewStyle,
  Text,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

interface ModalLayoutProps {
  visible: boolean;
  onClose: () => void;
  children: ReactNode;
  title?: string;
  fullScreen?: boolean;
  style?: ViewStyle;
}

export const ModalLayout: React.FC<ModalLayoutProps> = ({
  visible,
  onClose,
  children,
  title,
  fullScreen = false,
  style,
}) => {
  if (fullScreen) {
    return (
      <Modal
        visible={visible}
        animationType="slide"
        presentationStyle="fullScreen"
        onRequestClose={onClose}
      >
        <SafeAreaView style={styles.fullScreenRoot}>
          <View style={styles.fullScreenHeader}>
            {title ? (
              <Text style={styles.fullScreenTitle}>{title}</Text>
            ) : (
              <View />
            )}
            <TouchableOpacity onPress={onClose} style={styles.closeButton} hitSlop={styles.hitSlop}>
              <Text style={styles.closeIcon}>✕</Text>
            </TouchableOpacity>
          </View>
          <View style={[styles.fullScreenContent, style]}>{children}</View>
        </SafeAreaView>
      </Modal>
    );
  }

  // Bottom sheet style
  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onClose}
    >
      <TouchableOpacity
        style={styles.overlay}
        activeOpacity={1}
        onPress={onClose}
      />
      <View style={[styles.sheet, style]}>
        {/* Drag handle */}
        <View style={styles.dragHandleContainer}>
          <View style={styles.dragHandle} />
        </View>
        {title ? <Text style={styles.sheetTitle}>{title}</Text> : null}
        {children}
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  /* Full screen */
  fullScreenRoot: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  fullScreenHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#EBEEF0',
  },
  fullScreenTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#242D35',
  },
  closeButton: {
    width: 32,
    height: 32,
    alignItems: 'center',
    justifyContent: 'center',
  },
  closeIcon: {
    fontSize: 16,
    color: '#6B7580',
  },
  hitSlop: {
    top: 8,
    bottom: 8,
    left: 8,
    right: 8,
  },
  fullScreenContent: {
    flex: 1,
    paddingHorizontal: 16,
    paddingTop: 16,
  },

  /* Bottom sheet */
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.4)',
  },
  sheet: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingBottom: Platform.OS === 'ios' ? 34 : 16,
    paddingHorizontal: 16,
    paddingTop: 8,
  },
  dragHandleContainer: {
    alignItems: 'center',
    paddingVertical: 8,
  },
  dragHandle: {
    width: 135,
    height: 5,
    backgroundColor: '#EBEEF0',
    borderRadius: 100,
  },
  sheetTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#242D35',
    marginBottom: 16,
    textAlign: 'center',
  },
});

export default ModalLayout;

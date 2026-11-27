import React from 'react';
import Button from '@components/atoms/Button';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import { strings } from '@/strings';
import ConfirmDialog from './ConfirmDialog';

const copy = strings.transactions.deleteDialog;

export interface DeleteTransactionDialogProps {
  visible: boolean;
  message: string;
  loading: boolean;
  /** Why the last attempt failed. */
  error?: string;
  onConfirm: () => void;
  onDismiss: () => void;
}

/** 03-05B, opened from both Transaction Details and Edit Transaction. */
const DeleteTransactionDialog: React.FC<DeleteTransactionDialogProps> = ({
  visible,
  message,
  loading,
  error,
  onConfirm,
  onDismiss,
}) => (
  <ConfirmDialog
    visible={visible}
    title={copy.title}
    message={message}
    onDismiss={onDismiss}
    actions={
      <>
        {error ? <FeedbackBanner tone="error" title={error} /> : null}
        <Button title={copy.confirm} variant="danger" loading={loading} onPress={onConfirm} />
        <Button title={copy.keep} variant="outline" disabled={loading} onPress={onDismiss} />
      </>
    }
  />
);

export default DeleteTransactionDialog;

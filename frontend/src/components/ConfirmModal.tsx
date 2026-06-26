import { AlertTriangle, X } from 'lucide-react';

type ConfirmModalProps = {
  title: string;
  message: string;
  confirmLabel: string;
  busy?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

export function ConfirmModal({
  title,
  message,
  confirmLabel,
  busy = false,
  onCancel,
  onConfirm
}: ConfirmModalProps) {
  return (
    <div className="modalLayer" role="presentation">
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <div className="modalHeader">
          <div className="modalTitle">
            <AlertTriangle size={20} aria-hidden="true" />
            <h2 id="confirm-title">{title}</h2>
          </div>
          <button className="iconButton" type="button" onClick={onCancel} aria-label="Close">
            <X size={18} aria-hidden="true" />
          </button>
        </div>
        <p>{message}</p>
        <div className="modalActions">
          <button className="button secondary" type="button" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button className="button danger" type="button" onClick={onConfirm} disabled={busy}>
            {busy ? 'Working' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}


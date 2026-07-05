import { useEffect } from "react";

interface ConfirmDialogProps {
  title: string;
  description?: string;
  confirmLabel: string;
  cancelLabel?: string;
  destructive?: boolean;
  loading?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}

export default function ConfirmDialog({
  title,
  description,
  confirmLabel,
  cancelLabel = "Volver",
  destructive = false,
  loading = false,
  onConfirm,
  onClose,
}: ConfirmDialogProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const body = document.body;
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    const prevOverflow = body.style.overflow;
    const prevPaddingRight = body.style.paddingRight;
    body.style.overflow = "hidden";
    if (scrollbarWidth > 0) {
      const current = parseFloat(getComputedStyle(body).paddingRight) || 0;
      body.style.paddingRight = `${current + scrollbarWidth}px`;
    }
    return () => {
      document.removeEventListener("keydown", onKey);
      body.style.overflow = prevOverflow;
      body.style.paddingRight = prevPaddingRight;
    };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50">
      <div
        className="absolute inset-0 bg-black/60 animate-backdrop-in"
        onClick={onClose}
      />
      <div className="absolute inset-0 flex items-center justify-center px-4 pointer-events-none">
        <div
          role="dialog"
          aria-modal="true"
          className="pointer-events-auto w-full max-w-[400px] bg-panel border border-line rounded-2xl shadow-[0_24px_64px_rgba(0,0,0,0.4)] animate-fade-in"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="px-6 pt-6 pb-5">
            <h2 className="m-0 mb-1.5 text-[17px] font-bold tracking-[-0.01em]">{title}</h2>
            {description && (
              <p className="m-0 text-[13px] text-sub leading-relaxed">{description}</p>
            )}
          </div>
          <div className="flex items-center justify-end gap-2 px-6 pb-5">
            <button
              type="button"
              disabled={loading}
              onClick={onClose}
              className="h-[38px] px-[18px] bg-transparent border border-line-2 rounded-[9px] text-fg font-medium text-sm disabled:opacity-40"
            >
              {cancelLabel}
            </button>
            <button
              type="button"
              disabled={loading}
              onClick={onConfirm}
              className={`h-[38px] px-[18px] rounded-[9px] font-semibold text-sm disabled:opacity-40 ${
                destructive
                  ? "bg-neg text-white border border-neg"
                  : "bg-accent text-accent-ink border border-accent"
              }`}
            >
              {loading ? "Cancelando…" : confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

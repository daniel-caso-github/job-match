import { useEffect, useState, type ReactNode } from "react";

interface DrawerProps {
  onClose: () => void;
  children: (requestClose: () => void) => ReactNode;
}

export default function Drawer({ onClose, children }: DrawerProps) {
  const [closing, setClosing] = useState(false);
  const requestClose = () => setClosing(true);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setClosing(true);
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
  }, []);

  return (
    <div className="fixed inset-0 z-40">
      <div
        className={`absolute inset-0 bg-black/60 ${
          closing ? "animate-backdrop-out" : "animate-backdrop-in"
        }`}
        onClick={requestClose}
      />
      <aside
        role="dialog"
        aria-modal="true"
        onAnimationEnd={(e) => {
          if (closing && e.target === e.currentTarget) onClose();
        }}
        className={`absolute top-0 right-0 h-full w-full sm:w-[40vw] sm:min-w-[640px] bg-app border-l border-line-2 sm:rounded-l-2xl shadow-[-24px_0_48px_rgba(0,0,0,0.35)] overflow-y-auto ${
          closing ? "animate-slide-out" : "animate-slide-in"
        }`}
      >
        {children(requestClose)}
      </aside>
    </div>
  );
}

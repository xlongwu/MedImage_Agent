import {
  useEffect,
  useId,
  useRef,
  type KeyboardEvent as ReactKeyboardEvent,
  type MouseEvent,
  type ReactNode,
} from "react";

import { Button } from "./primitives";
import styles from "./overlays.module.css";

type OverlayProps = {
  children?: ReactNode;
  description?: ReactNode;
  footer?: ReactNode;
  open: boolean;
  title: ReactNode;
  onOpenChange: (open: boolean) => void;
};

export type DialogProps = OverlayProps & {
  closeLabel?: string;
};

export function Dialog({
  children,
  closeLabel = "Close dialog",
  description,
  footer,
  onOpenChange,
  open,
  title,
}: DialogProps) {
  const titleId = useId();
  const descriptionId = useId();
  const { handleKeyDown, surfaceRef } = useOverlayFocus(open);

  useEscapeToClose(open, onOpenChange);

  if (!open) {
    return null;
  }

  return (
    <div className={styles.backdrop} onMouseDown={(event) => closeOnBackdrop(event, onOpenChange)}>
      <section
        aria-describedby={description ? descriptionId : undefined}
        aria-labelledby={titleId}
        aria-modal="true"
        className={styles.dialog}
        onKeyDown={handleKeyDown}
        ref={surfaceRef}
        role="dialog"
        tabIndex={-1}
      >
        <OverlayHeader closeLabel={closeLabel} onClose={() => onOpenChange(false)} title={title} titleId={titleId} />
        {description ? (
          <p className={styles.description} id={descriptionId}>
            {description}
          </p>
        ) : null}
        {children ? <div className={styles.body}>{children}</div> : null}
        {footer ? <footer className={styles.footer}>{footer}</footer> : null}
      </section>
    </div>
  );
}

export type SheetProps = OverlayProps & {
  closeLabel?: string;
  side?: "right" | "bottom";
};

export function Sheet({
  children,
  closeLabel = "Close sheet",
  description,
  footer,
  onOpenChange,
  open,
  side = "right",
  title,
}: SheetProps) {
  const titleId = useId();
  const descriptionId = useId();
  const { handleKeyDown, surfaceRef } = useOverlayFocus(open);

  useEscapeToClose(open, onOpenChange);

  if (!open) {
    return null;
  }

  return (
    <div className={styles.backdrop} onMouseDown={(event) => closeOnBackdrop(event, onOpenChange)}>
      <aside
        aria-describedby={description ? descriptionId : undefined}
        aria-labelledby={titleId}
        aria-modal="true"
        className={`${styles.sheet} ${side === "bottom" ? styles.sheetBottom : styles.sheetRight}`}
        onKeyDown={handleKeyDown}
        ref={surfaceRef}
        role="dialog"
        tabIndex={-1}
      >
        <OverlayHeader closeLabel={closeLabel} onClose={() => onOpenChange(false)} title={title} titleId={titleId} />
        {description ? (
          <p className={styles.description} id={descriptionId}>
            {description}
          </p>
        ) : null}
        <div className={styles.sheetBody}>{children}</div>
        {footer ? <footer className={styles.footer}>{footer}</footer> : null}
      </aside>
    </div>
  );
}

function OverlayHeader({
  closeLabel,
  onClose,
  title,
  titleId,
}: {
  closeLabel: string;
  onClose: () => void;
  title: ReactNode;
  titleId: string;
}) {
  return (
    <header className={styles.header}>
      <h2 id={titleId}>{title}</h2>
      <Button aria-label={closeLabel} className={styles.closeButton} onClick={onClose} size="sm" variant="ghost">
        <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
          <path
            fill="none"
            stroke="currentColor"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="1.8"
            d="M4 4l8 8M12 4l-8 8"
          />
        </svg>
      </Button>
    </header>
  );
}

function closeOnBackdrop(
  event: MouseEvent<HTMLDivElement>,
  onOpenChange: (open: boolean) => void,
) {
  if (event.target === event.currentTarget) {
    onOpenChange(false);
  }
}

function useEscapeToClose(open: boolean, onOpenChange: (open: boolean) => void) {
  useEffect(() => {
    if (!open) {
      return undefined;
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onOpenChange(false);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onOpenChange]);
}

const focusableSelector = [
  "a[href]",
  "button:not([disabled])",
  "textarea:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

function getFocusableElements(root: HTMLElement | null): HTMLElement[] {
  if (!root) return [];
  return Array.from(root.querySelectorAll<HTMLElement>(focusableSelector)).filter(
    (element) => !element.hasAttribute("aria-hidden"),
  );
}

function useOverlayFocus(open: boolean) {
  const surfaceRef = useRef<HTMLElement | null>(null);
  const restoreFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) {
      return undefined;
    }

    restoreFocusRef.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const frame = window.requestAnimationFrame(() => {
      const firstFocusable = getFocusableElements(surfaceRef.current)[0];
      (firstFocusable ?? surfaceRef.current)?.focus();
    });

    return () => {
      window.cancelAnimationFrame(frame);
      restoreFocusRef.current?.focus();
      restoreFocusRef.current = null;
    };
  }, [open]);

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLElement>) => {
    if (event.key !== "Tab") {
      return;
    }

    const focusableElements = getFocusableElements(surfaceRef.current);
    if (!focusableElements.length) {
      event.preventDefault();
      surfaceRef.current?.focus();
      return;
    }

    const first = focusableElements[0];
    const last = focusableElements[focusableElements.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  return { handleKeyDown, surfaceRef };
}

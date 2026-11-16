import { useEffect, useRef } from "react";
/** Keep keyboard focus inside a modal, then restore its invoking control. */
export function useDialogFocus(open: boolean, onClose: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  const lastOutsideFocus = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (!open) {
      const remember = (event: FocusEvent) => {
        const target = event.target;
        if (target instanceof HTMLElement && !target.closest('[role="dialog"]'))
          lastOutsideFocus.current = target;
      };
      document.addEventListener("focusin", remember);
      return () => document.removeEventListener("focusin", remember);
    }
    const previous = lastOutsideFocus.current;
    const controls = () =>
      Array.from(
        ref.current?.querySelectorAll<HTMLElement>(
          'button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),textarea:not(:disabled),[tabindex="0"]',
        ) ?? [],
      ).filter((el) => el.getClientRects().length > 0);
    const first = controls()[0];
    first?.focus();
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab") return;
      const nodes = controls();
      if (!nodes.length) {
        event.preventDefault();
        return;
      }
      const index = nodes.indexOf(document.activeElement as HTMLElement);
      if (event.shiftKey && index <= 0) {
        event.preventDefault();
        nodes[nodes.length - 1]?.focus();
      } else if (!event.shiftKey && (index === nodes.length - 1 || index < 0)) {
        event.preventDefault();
        nodes[0].focus();
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      if (previous?.isConnected) previous.focus();
    };
  }, [open, onClose]);
  return ref;
}

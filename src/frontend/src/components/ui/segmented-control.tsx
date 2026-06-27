import { type KeyboardEvent } from "react";

import styles from "./segmented-control.module.css";

export type SegmentedControlOption = {
  disabled?: boolean;
  label: string;
  value: string;
};

export type SegmentedControlProps = {
  "aria-label": string;
  className?: string;
  options: SegmentedControlOption[];
  value: string;
  onChange: (value: string) => void;
};

export function SegmentedControl({
  "aria-label": ariaLabel,
  className,
  onChange,
  options,
  value,
}: SegmentedControlProps) {
  const enabledOptions = options.filter((option) => !option.disabled);

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key) || enabledOptions.length === 0) {
      return;
    }

    event.preventDefault();
    const currentIndex = Math.max(
      0,
      enabledOptions.findIndex((option) => option.value === value),
    );
    if (event.key === "Home") {
      onChange(enabledOptions[0].value);
      return;
    }
    if (event.key === "End") {
      onChange(enabledOptions[enabledOptions.length - 1].value);
      return;
    }

    const direction = event.key === "ArrowRight" ? 1 : -1;
    const nextIndex = (currentIndex + direction + enabledOptions.length) % enabledOptions.length;
    onChange(enabledOptions[nextIndex].value);
  };

  return (
    <div
      aria-label={ariaLabel}
      className={`${styles.segmentedControl} ${className ?? ""}`}
      onKeyDown={handleKeyDown}
      role="radiogroup"
    >
      {options.map((option) => {
        const selected = option.value === value;
        return (
          <button
            aria-checked={selected}
            className={selected ? styles.selected : undefined}
            disabled={option.disabled}
            key={option.value}
            onClick={() => onChange(option.value)}
            role="radio"
            tabIndex={selected ? 0 : -1}
            type="button"
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

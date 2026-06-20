import React from "react";

interface Props {
  currentStep: number;
  labels: string[];
  onStepClick: (step: number) => void;
}

export function WorkflowStepper({ currentStep, labels, onStepClick }: Props) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        gap: 0,
        marginBottom: 8,
        flexWrap: "wrap",
      }}
    >
      {labels.map((label, i) => (
        <div
          key={i}
          onClick={() => onStepClick(i)}
          style={{
            display: "flex",
            alignItems: "center",
            cursor: "pointer",
            opacity: i <= currentStep + 1 ? 1 : 0.4,
          }}
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: "50%",
              background: i === currentStep ? "#1976d2" : i < currentStep ? "#4caf50" : "#e0e0e0",
              color: i <= currentStep ? "#fff" : "#666",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 700,
              fontSize: 14,
            }}
          >
            {i < currentStep ? "✓" : i + 1}
          </div>
          <span
            style={{
              marginLeft: 6,
              fontSize: 12,
              fontWeight: i === currentStep ? 700 : 400,
              color: i === currentStep ? "#1976d2" : "#666",
              whiteSpace: "nowrap",
            }}
          >
            {label}
          </span>
          {i < labels.length - 1 && (
            <div
              style={{
                width: 28,
                height: 2,
                background: i < currentStep ? "#4caf50" : "#e0e0e0",
                margin: "0 4px",
              }}
            />
          )}
        </div>
      ))}
    </div>
  );
}

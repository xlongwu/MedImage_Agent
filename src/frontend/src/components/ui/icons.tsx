import type { SVGProps } from "react";

type IconName =
  | "arrow-left"
  | "chevron-down"
  | "circle-alert"
  | "circle-check"
  | "folder"
  | "inspector"
  | "language"
  | "plus"
  | "runs"
  | "settings"
  | "spark";

const paths: Record<IconName, string[]> = {
  "arrow-left": ["M13 8H3", "m7-5-5 5 5 5"],
  "chevron-down": ["m4 6 4 4 4-4"],
  "circle-alert": ["M8 14a6 6 0 1 0 0-12 6 6 0 0 0 0 12Z", "M8 5v4", "M8 11.5h.01"],
  "circle-check": ["M8 14a6 6 0 1 0 0-12 6 6 0 0 0 0 12Z", "m5.5 8 1.6 1.6 3.5-3.8"],
  folder: ["M2 4.5h4l1.2 1.4H14v6.6H2Z"],
  inspector: ["M3 3.5h10", "M3 8h10", "M3 12.5h6", "m11 11 1.5 1.5 2-2"],
  language: [
    "M2.5 4h7",
    "M6 2.5V4",
    "M4 4c.4 2.2 1.7 3.8 4 5",
    "M8 4c-.4 2.2-1.7 3.8-4 5",
    "m9 7 2 5",
    "m14 12-2-5-2 5",
    "m10.7 10.2h2.6",
  ],
  plus: ["M8 3v10", "M3 8h10"],
  runs: ["M3 3.5h10v9H3Z", "M5.5 6h5", "M5.5 9h3"],
  settings: [
    "M8 5.4A2.6 2.6 0 1 0 8 10.6 2.6 2.6 0 0 0 8 5.4Z",
    "M8 2v1.4",
    "M8 12.6V14",
    "M2 8h1.4",
    "M12.6 8H14",
    "m3.8 3.8 1 1",
    "m11.2 11.2 1 1",
    "m12.2 3.8-1 1",
    "m4.8 11.2-1 1",
  ],
  spark: ["M8 2.5 9.1 5.7 12.5 7 9.1 8.3 8 11.5 6.9 8.3 3.5 7l3.4-1.3Z"],
};

export function Icon({ name, ...props }: SVGProps<SVGSVGElement> & { name: IconName }) {
  return (
    <svg
      {...props}
      aria-hidden={props["aria-label"] ? undefined : true}
      fill="none"
      viewBox="0 0 16 16"
    >
      {paths[name].map((path) => (
        <path
          d={path}
          fill="none"
          key={path}
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="1.5"
        />
      ))}
    </svg>
  );
}

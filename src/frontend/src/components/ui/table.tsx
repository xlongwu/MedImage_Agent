import {
  type HTMLAttributes,
  type ReactNode,
  type Ref,
  type TableHTMLAttributes,
} from "react";

import styles from "./table.module.css";

export type TableProps = TableHTMLAttributes<HTMLTableElement> & {
  caption?: ReactNode;
  viewportClassName?: string;
  viewportProps?: HTMLAttributes<HTMLDivElement>;
  viewportRef?: Ref<HTMLDivElement>;
};

export function Table({
  caption,
  children,
  className,
  viewportClassName,
  viewportProps,
  viewportRef,
  ...props
}: TableProps) {
  const { className: viewportPropsClassName, ...remainingViewportProps } = viewportProps ?? {};

  return (
    <div
      {...remainingViewportProps}
      ref={viewportRef}
      className={[styles.tableViewport, viewportClassName, viewportPropsClassName]
        .filter(Boolean)
        .join(" ")}
    >
      <table {...props} className={`${styles.table} ${className ?? ""}`}>
        {caption ? <caption>{caption}</caption> : null}
        {children}
      </table>
    </div>
  );
}

export function TableEmpty({
  children,
  className,
  colSpan,
  ...props
}: HTMLAttributes<HTMLTableRowElement> & {
  colSpan: number;
}) {
  return (
    <tr {...props} className={className}>
      <td className={styles.emptyCell} colSpan={colSpan}>
        {children}
      </td>
    </tr>
  );
}

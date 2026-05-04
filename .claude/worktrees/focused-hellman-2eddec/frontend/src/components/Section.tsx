import type { ReactNode } from "react";

type Props = {
  title: string;
  description?: string;
  children: ReactNode;
};

export function Section({ title, description, children }: Props) {
  return (
    <section className="section">
      <div className="sectionHeader">
        <h2>{title}</h2>
        {description ? <p>{description}</p> : null}
      </div>
      <div>{children}</div>
    </section>
  );
}

export interface MetricCardProps {
  title: string;
  values: Array<[string, string]>;
  tone: string;
  note?: string;
}

export function MetricCard({ title, values, tone, note }: MetricCardProps) {
  return (
    <section className={`metric-card ${tone}`}>
      <div className="card-row">
        <div className="card-title">{title}</div>
        {note ? <span className="micro-badge">{note}</span> : null}
      </div>
      <div className="metric-grid">
        {values.map(([value, label]) => (
          <div key={label}>
            <strong>{value}</strong>
            <span>{label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

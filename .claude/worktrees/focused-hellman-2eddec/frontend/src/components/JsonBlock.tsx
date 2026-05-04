type Props = {
  value: unknown;
  emptyText?: string;
};

export function JsonBlock({ value, emptyText = "No data" }: Props) {
  if (value === null || value === undefined) {
    return <div className="empty">{emptyText}</div>;
  }

  return (
    <pre className="codeBlock">
      {typeof value === "string" ? value : JSON.stringify(value, null, 2)}
    </pre>
  );
}

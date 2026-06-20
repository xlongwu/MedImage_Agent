export function MiniScan({ axis }: { axis: string }) {
  return (
    <>
      <div className="mini-scan-core" />
      <span>{axis}</span>
    </>
  );
}

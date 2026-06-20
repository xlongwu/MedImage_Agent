type BarDatum = {
  label: string;
  value: number;
};

type LineDatum = {
  label: string;
  value: number;
};

type Props = {
  title: string;
};

export function SimpleBarChart({ title, data }: Props & { data: BarDatum[] }) {
  const maxValue = Math.max(...data.map((item) => item.value), 1);

  return (
    <div className="chartCard" style={{ marginBottom: 16 }}>
      <h4 style={{ margin: "0 0 12px 0", fontSize: 14 }}>{title}</h4>
      <div className="barChart">
        {data.map((item) => (
          <div
            className="barRow"
            key={item.label}
            style={{ display: "flex", alignItems: "center", marginBottom: 6 }}
          >
            <div
              className="barLabel"
              style={{ width: 100, fontSize: 12, overflow: "hidden", textOverflow: "ellipsis" }}
            >
              {item.label}
            </div>
            <div
              className="barTrack"
              style={{
                flex: 1,
                height: 16,
                background: "#e0e0e0",
                borderRadius: 2,
                marginRight: 8,
              }}
            >
              <div
                className="barFill"
                style={{
                  width: `${(item.value / maxValue) * 100}%`,
                  height: "100%",
                  background: "#2196f3",
                  borderRadius: 2,
                }}
              />
            </div>
            <div className="barValue" style={{ width: 40, fontSize: 12, textAlign: "right" }}>
              {item.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SimpleLineChart({ title, data }: Props & { data: LineDatum[] }) {
  const width = 520;
  const height = 180;
  const padding = 24;
  const maxValue = Math.max(...data.map((item) => item.value), 1);
  const minValue = Math.min(...data.map((item) => item.value), 0);
  const span = Math.max(maxValue - minValue, 1);

  const points = data.map((item, index) => {
    const x =
      data.length === 1 ? width / 2 : padding + (index / (data.length - 1)) * (width - padding * 2);
    const y = height - padding - ((item.value - minValue) / span) * (height - padding * 2);

    return { x, y, label: item.label, value: item.value };
  });

  const path = points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`)
    .join(" ");

  return (
    <div className="chartCard" style={{ marginBottom: 16 }}>
      <h4 style={{ margin: "0 0 12px 0", fontSize: 14 }}>{title}</h4>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="lineChart"
        style={{ width: "100%", maxWidth: 540 }}
      >
        <line
          x1={padding}
          y1={height - padding}
          x2={width - padding}
          y2={height - padding}
          stroke="#ccc"
        />
        <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="#ccc" />
        <path d={path} fill="none" stroke="#2196f3" strokeWidth="2" />
        {points.map((point, idx) => (
          <circle key={idx} cx={point.x} cy={point.y} r="3" fill="#2196f3" />
        ))}
      </svg>
      <div className="chartHint" style={{ fontSize: 12, color: "#666", marginTop: 8 }}>
        {data.length} points · max {maxValue}
      </div>
    </div>
  );
}

export function SimplePieChart({ title, data }: Props & { data: BarDatum[] }) {
  const total = data.reduce((sum, item) => sum + item.value, 0);
  const colors = ["#4caf50", "#f44336", "#ff9800", "#2196f3", "#9c27b0", "#607d8b"];

  let currentAngle = 0;
  const slices = data.map((item, index) => {
    const angle = (item.value / total) * 360;
    const startAngle = currentAngle;
    const endAngle = currentAngle + angle;
    currentAngle += angle;

    const startRad = (startAngle * Math.PI) / 180;
    const endRad = (endAngle * Math.PI) / 180;

    const cx = 60;
    const cy = 60;
    const r = 50;

    const x1 = cx + r * Math.cos(startRad);
    const y1 = cy + r * Math.sin(startRad);
    const x2 = cx + r * Math.cos(endRad);
    const y2 = cy + r * Math.sin(endRad);

    const largeArc = angle > 180 ? 1 : 0;

    const path = `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`;

    return { path, color: colors[index % colors.length], label: item.label, value: item.value };
  });

  return (
    <div className="chartCard" style={{ marginBottom: 16 }}>
      <h4 style={{ margin: "0 0 12px 0", fontSize: 14 }}>{title}</h4>
      <div style={{ display: "flex", alignItems: "center" }}>
        <svg viewBox="0 0 120 120" style={{ width: 120, height: 120 }}>
          {slices.map((slice, idx) => (
            <path key={idx} d={slice.path} fill={slice.color} />
          ))}
        </svg>
        <div style={{ marginLeft: 16 }}>
          {slices.map((slice, idx) => (
            <div
              key={idx}
              style={{ display: "flex", alignItems: "center", marginBottom: 4, fontSize: 12 }}
            >
              <div
                style={{
                  width: 12,
                  height: 12,
                  background: slice.color,
                  marginRight: 8,
                  borderRadius: 2,
                }}
              />
              <span>
                {slice.label}: {slice.value} ({((slice.value / total) * 100).toFixed(1)}%)
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

interface TextViewerProps {
  text: string;
  emptyText?: string;
  parsed?: unknown;
  truncated?: boolean;
  previewType?: string;
  maxHeight?: string;
}

export function TextViewer({
  text,
  parsed,
  truncated,
  previewType,
  maxHeight = "400px"
}: TextViewerProps) {
  if (previewType === "nifti_metadata" && parsed && typeof parsed === "object") {
    const metadata = parsed as Record<string, unknown>;
    return (
      <div style={{ padding: 12, background: "#f5f5f5", borderRadius: 4 }}>
        <div style={{ marginBottom: 8, fontWeight: "bold" }}>NIfTI Metadata</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 8 }}>
          {metadata.shape && (
            <div>
              <strong>Shape:</strong> {JSON.stringify(metadata.shape)}
            </div>
          )}
          {metadata.dtype && (
            <div>
              <strong>Data Type:</strong> {String(metadata.dtype)}
            </div>
          )}
          {metadata.zooms && (
            <div>
              <strong>Voxel Size:</strong> {JSON.stringify(metadata.zooms)}
            </div>
          )}
        </div>
        {metadata.note && (
          <div style={{ marginTop: 8, fontSize: 12, color: "#666" }}>
            {String(metadata.note)}
          </div>
        )}
        {metadata.error && (
          <div style={{ marginTop: 8, color: "red" }}>
            Error: {String(metadata.error)}
          </div>
        )}
      </div>
    );
  }

  if (previewType === "metadata_only") {
    return (
      <div style={{ padding: 12, background: "#f5f5f5", borderRadius: 4, color: "#666" }}>
        Preview is not supported for this file type.
      </div>
    );
  }

  const isJson = parsed !== null && parsed !== undefined;

  return (
    <div>
      {isJson && (
        <div style={{ marginBottom: 8 }}>
          <details>
            <summary style={{ cursor: "pointer", color: "#2196f3" }}>
              View Parsed JSON
            </summary>
            <pre
              style={{
                background: "#f5f5f5",
                padding: 12,
                borderRadius: 4,
                overflow: "auto",
                maxHeight,
                fontSize: 12,
                marginTop: 8
              }}
            >
              {JSON.stringify(parsed, null, 2)}
            </pre>
          </details>
        </div>
      )}
      <pre
        style={{
          background: "#f5f5f5",
          padding: 12,
          borderRadius: 4,
          overflow: "auto",
          maxHeight,
          fontSize: 12,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word"
        }}
      >
        {text}
      </pre>
      {truncated && (
        <div style={{ marginTop: 8, fontSize: 12, color: "#ff9800" }}>
          ⚠️ Content truncated. File is larger than preview limit.
        </div>
      )}
    </div>
  );
}

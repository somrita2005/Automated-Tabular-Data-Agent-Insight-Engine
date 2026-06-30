import { useState, useRef } from "react";

export default function UploadPanel({ onUpload, onSample }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef();

  async function handleFile(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("Only CSV files are supported.");
      return;
    }
    setUploading(true);
    setError("");
    try {
      await onUpload(file);
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleSample() {
    setUploading(true);
    setError("");
    try {
      await onSample();
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="upload-page">
      <div className="upload-hero">
        <h1 className="hero-title">Ask your data anything.</h1>
        <p className="hero-sub">
          Upload a CSV and chat with it in plain English.<br />
          The agent writes and runs the queries — you just ask.
        </p>

        <div
          className={`drop-zone ${dragging ? "drop-zone--active" : ""} ${uploading ? "drop-zone--loading" : ""}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={e => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={e => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]); }}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".csv"
            style={{ display: "none" }}
            onChange={e => handleFile(e.target.files[0])}
          />
          <div className="drop-icon">{uploading ? "⟳" : "↑"}</div>
          <div className="drop-text">
            {uploading ? "Loading dataset…" : "Drop a CSV here or click to browse"}
          </div>
          <div className="drop-hint">Up to ~50MB · UTF-8 · any structure</div>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <div className="divider"><span>or</span></div>

        <button className="btn-sample" onClick={handleSample} disabled={uploading}>
          Try sample NGO survey dataset
          <span className="sample-meta">300 rows · sanitation &amp; water indicators</span>
        </button>
      </div>

      <div className="example-queries">
        <div className="eq-label">Example questions you can ask</div>
        <div className="eq-grid">
          {[
            { q: "Which region had the highest dropout rate?", icon: "📍" },
            { q: "Show me survey completions by month", icon: "📈" },
            { q: "What's the average satisfaction score by region?", icon: "⭐" },
            { q: "Are there anomalies in household income?", icon: "🔍" },
            { q: "Pie chart of primary water sources", icon: "🥧" },
            { q: "How many surveys does each field worker have?", icon: "👤" },
          ].map(item => (
            <div key={item.q} className="eq-card">
              <span className="eq-icon">{item.icon}</span>
              <span className="eq-text">"{item.q}"</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

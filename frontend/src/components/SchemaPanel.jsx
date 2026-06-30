import { useState } from "react";

export default function SchemaPanel({ schema, columns, rows }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside className={`schema-panel ${collapsed ? "schema-panel--collapsed" : ""}`}>
      <button className="schema-toggle" onClick={() => setCollapsed(c => !c)} title="Toggle schema">
        {collapsed ? "›" : "‹"}
      </button>

      {!collapsed && (
        <>
          <div className="schema-header">
            <div className="schema-title">Dataset</div>
            <div className="schema-meta">
              <span className="meta-chip">{rows?.toLocaleString()} rows</span>
              <span className="meta-chip">{columns?.length} cols</span>
            </div>
          </div>

          <div className="schema-body">
            <div className="schema-section-label">Columns</div>
            <div className="col-list">
              {columns?.map(col => (
                <div key={col} className="col-item">
                  <span className="col-dot" />
                  <span className="col-name">{col}</span>
                </div>
              ))}
            </div>

            <div className="schema-section-label" style={{ marginTop: "16px" }}>
              SQL Schema
            </div>
            <pre className="schema-pre">{schema}</pre>
          </div>

          <div className="schema-tip">
            Table name: <code>data</code>
          </div>
        </>
      )}
    </aside>
  );
}

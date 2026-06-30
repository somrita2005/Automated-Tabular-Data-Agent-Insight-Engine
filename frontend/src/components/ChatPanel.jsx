import { useState, useRef, useEffect } from "react";

function MessageBubble({ msg }) {
  const isUser = msg.role === "user";

  function renderMarkdown(text) {
    // Very lightweight markdown: bold, code, newlines
    return text
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/`(.+?)`/g, "<code>$1</code>")
      .replace(/\n/g, "<br/>");
  }

  return (
    <div className={`message-row ${isUser ? "message-row--user" : "message-row--agent"}`}>
      {!isUser && <div className="avatar avatar--agent">⬡</div>}
      <div className={`bubble ${isUser ? "bubble--user" : "bubble--agent"}`}>
        {msg.text && (
          <div
            className="bubble-text"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.text) }}
          />
        )}

        {msg.charts && msg.charts.map((chart, i) => (
          <div key={i} className="chart-container">
            <div className="chart-title">{chart.title}</div>
            <img
              src={`data:image/png;base64,${chart.image_base64}`}
              alt={chart.title}
              className="chart-img"
            />
          </div>
        ))}

        {msg.toolCalls && msg.toolCalls.length > 0 && (
          <ToolCallsAccordion calls={msg.toolCalls} />
        )}
      </div>
      {isUser && <div className="avatar avatar--user">S</div>}
    </div>
  );
}

function ToolCallsAccordion({ calls }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="tool-calls">
      <button className="tool-calls-toggle" onClick={() => setOpen(o => !o)}>
        {open ? "▾" : "▸"} {calls.length} tool call{calls.length > 1 ? "s" : ""}
      </button>
      {open && (
        <div className="tool-calls-list">
          {calls.map((c, i) => (
            <div key={i} className={`tool-call-item ${c.ok ? "tool-call-item--ok" : "tool-call-item--err"}`}>
              <span className="tc-status">{c.ok ? "✓" : "✗"}</span>
              <span className="tc-name">{c.tool}</span>
              {c.tool === "run_sql_query" && c.input?.query && (
                <code className="tc-sql">{c.input.query}</code>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="message-row message-row--agent">
      <div className="avatar avatar--agent">⬡</div>
      <div className="bubble bubble--agent bubble--typing">
        <span className="dot" /><span className="dot" /><span className="dot" />
      </div>
    </div>
  );
}

const SUGGESTIONS = [
  "Which region has the highest dropout rate?",
  "Show a bar chart of survey status",
  "Average satisfaction score by region",
  "Detect anomalies in monthly income",
  "Trend of surveys completed per month",
  "How many records per surveyor?",
];

export default function ChatPanel({ messages, loading, onSend }) {
  const [input, setInput] = useState("");
  const bottomRef = useRef();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function send() {
    const t = input.trim();
    if (!t || loading) return;
    setInput("");
    onSend(t);
  }

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div className="chat-panel">
      <div className="messages-area">
        {messages.map((msg, i) => (
          <MessageBubble key={i} msg={msg} />
        ))}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {messages.length <= 1 && !loading && (
        <div className="suggestions">
          {SUGGESTIONS.map(s => (
            <button key={s} className="suggestion-chip" onClick={() => onSend(s)}>
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="input-bar">
        <textarea
          className="chat-input"
          rows={1}
          placeholder="Ask a question about your data…"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          disabled={loading}
        />
        <button
          className={`send-btn ${loading ? "send-btn--loading" : ""}`}
          onClick={send}
          disabled={loading || !input.trim()}
        >
          {loading ? "⟳" : "↑"}
        </button>
      </div>
    </div>
  );
}

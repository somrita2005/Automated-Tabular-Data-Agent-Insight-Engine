import { useState, useRef, useEffect } from "react";
import UploadPanel from "./components/UploadPanel";
import ChatPanel from "./components/ChatPanel";
import SchemaPanel from "./components/SchemaPanel";

export default function App() {
  const [session, setSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const API = import.meta.env.VITE_API_URL || "http://localhost:5000";

  async function handleUpload(file) {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API}/api/upload`, { method: "POST", body: form });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    setSession(data);
    setMessages([{
      role: "assistant",
      text: `Dataset loaded ✓ — **${data.rows.toLocaleString()} rows × ${data.columns.length} columns**\n\nAsk me anything about your data. Try:\n- "Which region has the highest dropout rate?"\n- "Show a bar chart of survey status breakdown"\n- "What's the average satisfaction score by region?"`,
      charts: [],
    }]);
  }

  async function handleSample() {
    const res = await fetch(`${API}/api/sample`);
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    setSession(data);
    setMessages([{
      role: "assistant",
      text: `Sample NGO survey dataset loaded ✓ — **${data.rows.toLocaleString()} rows × ${data.columns.length} columns**\n\nThis is real-world style sanitation survey data. Try:\n- "Which region had the highest dropout rate?"\n- "Show me a trend of survey completions over time"\n- "Are there any anomalies in monthly income?"`,
      charts: [],
    }]);
  }

  async function handleSend(text) {
    if (!session || !text.trim()) return;

    const userMsg = { role: "user", text };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await fetch(`${API}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: session.session_id, message: text }),
      });
      const data = await res.json();
      if (data.error) {
        setMessages(prev => [...prev, { role: "assistant", text: `⚠️ ${data.error}`, charts: [] }]);
      } else {
        setMessages(prev => [...prev, {
          role: "assistant",
          text: data.text,
          charts: data.charts || [],
          toolCalls: data.tool_calls || [],
        }]);
      }
    } catch (e) {
      setMessages(prev => [...prev, { role: "assistant", text: `⚠️ Network error: ${e.message}`, charts: [] }]);
    } finally {
      setLoading(false);
    }
  }

  async function handleReset() {
    if (!session) return;
    await fetch(`${API}/api/session/${session.session_id}/reset`, { method: "POST" });
    setMessages([{
      role: "assistant",
      text: "Conversation cleared. Dataset is still loaded — ask me anything!",
      charts: [],
    }]);
  }

  function handleNewFile() {
    setSession(null);
    setMessages([]);
  }

  return (
    <div className="app-shell">
      <header className="top-bar">
        <div className="logo">
          <span className="logo-icon">⬡</span>
          <span className="logo-text">QueryAgent</span>
          <span className="logo-sub">Natural-language data analysis</span>
        </div>
        {session && (
          <div className="header-actions">
            <span className="file-badge">{session.filename}</span>
            <button className="btn-ghost" onClick={handleReset}>Clear chat</button>
            <button className="btn-ghost" onClick={handleNewFile}>New file</button>
          </div>
        )}
      </header>

      <main className="main-area">
        {!session ? (
          <UploadPanel onUpload={handleUpload} onSample={handleSample} />
        ) : (
          <div className="workspace">
            <SchemaPanel schema={session.schema} columns={session.columns} rows={session.rows} />
            <ChatPanel
              messages={messages}
              loading={loading}
              onSend={handleSend}
            />
          </div>
        )}
      </main>
    </div>
  );
}

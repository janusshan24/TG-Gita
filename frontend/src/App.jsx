import { useState, useRef, useEffect } from "react";
import ChatMessage from "./components/ChatMessage";
import SourceCard from "./components/SourceCard";
import "./index.css";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const WELCOME = {
  role: "assistant",
  content:
    "Hare Krishna! 🙏 I am your guide to the Bhagavad-gita As It Is by Srila Prabhupada. " +
    "Ask me anything about its teachings — karma, dharma, bhakti, the nature of the soul, or any specific verse.",
  sources: [],
};

const SUGGESTED = [
  "What does Krishna say about the soul in Chapter 2?",
  "Explain the concept of nishkama karma",
  "What is the meaning of BG 18.66?",
  "How should one perform their duties?",
];

export default function App() {
  const [messages, setMessages]   = useState([WELCOME]);
  const [input, setInput]         = useState("");
  const [loading, setLoading]     = useState(false);
  const [sources, setSources]     = useState([]);
  const bottomRef = useRef(null);
  const inputRef  = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const historyForApi = () =>
    messages
      .filter((m) => m.role !== "system")
      .map(({ role, content }) => ({ role, content }));

  const sendMessage = async (question) => {
    if (!question.trim() || loading) return;

    const userMsg = { role: "user", content: question };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setSources([]);

    // Placeholder for assistant streaming response
    setMessages((prev) => [...prev, { role: "assistant", content: "", sources: [] }]);

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          history: historyForApi(),
        }),
      });

      if (!res.ok) throw new Error(`Server error ${res.status}`);

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let   buffer  = "";
      let   fullText = "";
      let   finalSources = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6);

          if (raw === "__DONE__") break;

          let chunk;
          try { chunk = JSON.parse(raw); } catch { continue; }

          if (typeof chunk === "string") {
            if (chunk.startsWith("__SOURCES__")) {
              try {
                finalSources = JSON.parse(chunk.replace("__SOURCES__", ""));
              } catch { /* ignore */ }
            } else if (chunk.startsWith("__ERROR__")) {
              fullText += "\n\n⚠️ An error occurred. Please try again.";
            } else {
              fullText += chunk;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  role: "assistant",
                  content: fullText,
                  sources: [],
                };
                return updated;
              });
            }
          }
        }
      }

      // Attach sources to the last message
      setSources(finalSources);
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: fullText || "I'm sorry, I could not generate a response.",
          sources: finalSources,
        };
        return updated;
      });
    } catch (err) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: "⚠️ Could not connect to the server. Please ensure the backend is running.",
          sources: [],
        };
        return updated;
      });
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(input);
  };

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="header">
        <div className="header-inner">
          <span className="header-logo">🕉️</span>
          <div>
            <h1 className="header-title">Gita Chatbot</h1>
            <p className="header-subtitle">Bhagavad-gita As It Is · Srila Prabhupada</p>
          </div>
        </div>
      </header>

      {/* ── Chat window ── */}
      <main className="chat-window">
        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} />
        ))}

        {loading && (
          <div className="typing-indicator">
            <span /><span /><span />
          </div>
        )}

        {/* Suggested questions — show only at the start */}
        {messages.length === 1 && !loading && (
          <div className="suggestions">
            {SUGGESTED.map((q) => (
              <button
                key={q}
                className="suggestion-chip"
                onClick={() => sendMessage(q)}
              >
                {q}
              </button>
            ))}
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      {/* ── Input ── */}
      <footer className="input-area">
        <form className="input-form" onSubmit={handleSubmit}>
          <input
            ref={inputRef}
            className="input-box"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything about the Bhagavad-gita…"
            disabled={loading}
            autoFocus
          />
          <button
            className="send-btn"
            type="submit"
            disabled={loading || !input.trim()}
          >
            {loading ? "…" : "Send"}
          </button>
        </form>
        <p className="disclaimer">
          Answers are based on Srila Prabhupada's purports. Always refer to the{" "}
          <a href="https://vedabase.io/en/library/bg/" target="_blank" rel="noreferrer">
            full text
          </a>{" "}
          for complete understanding.
        </p>
      </footer>
    </div>
  );
}

import SourceCard from "./SourceCard";

export default function ChatMessage({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`message-row ${isUser ? "user-row" : "assistant-row"}`}>
      {!isUser && (
        <div className="avatar assistant-avatar" title="Gita Bot">
          🕉️
        </div>
      )}

      <div className={`bubble ${isUser ? "user-bubble" : "assistant-bubble"}`}>
        {/* Message text — support basic newlines */}
        <div className="bubble-text">
          {message.content.split("\n").map((line, i) => (
            <span key={i}>
              {line}
              {i < message.content.split("\n").length - 1 && <br />}
            </span>
          ))}
        </div>

        {/* Source citations */}
        {message.sources && message.sources.length > 0 && (
          <div className="sources-section">
            <p className="sources-label">📜 Sources</p>
            <div className="sources-list">
              {message.sources.map((src) => (
                <SourceCard key={src.reference} source={src} />
              ))}
            </div>
          </div>
        )}
      </div>

      {isUser && (
        <div className="avatar user-avatar" title="You">
          🙏
        </div>
      )}
    </div>
  );
}

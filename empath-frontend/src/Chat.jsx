import React, { useState, useRef, useEffect } from "react";
import axios from "axios";
import "./Chat.css";
import { Link } from "react-router-dom";

/**
 * Chat.jsx
 * - Left retractable sidebar (like ChatGPT)
 * - Main chat area with messages and input composer
 * - Sends messages to /api/chat (POST { userId, message, countryCode })
 *
 * Usage:
 *  - Add route: <Route path="/chat" element={<Chat />} />
 *  - Make sure react-router-dom and axios are installed.
 */

export default function Chat() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [conversations, setConversations] = useState(() => {
    // load from localStorage if present
    try {
      const raw = localStorage.getItem("empath_conversations");
      return raw ? JSON.parse(raw) : [{ id: "c1", title: "New chat", messages: [] }];
    } catch {
      return [{ id: "c1", title: "New chat", messages: [] }];
    }
  });
  const [activeConvIndex, setActiveConvIndex] = useState(0);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const listRef = useRef();

  const activeConv = conversations[activeConvIndex];

  useEffect(() => {
    // persist conversations
    localStorage.setItem("empath_conversations", JSON.stringify(conversations));
  }, [conversations]);

  useEffect(() => {
    // scroll to bottom when messages change
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [activeConv.messages.length]);

  function newChat() {
    const id = `c${Date.now()}`;
    const conv = { id, title: "New chat", messages: [] };
    setConversations(prev => [conv, ...prev]);
    setActiveConvIndex(0);
  }

  function selectChat(i) {
    setActiveConvIndex(i);
  }

  async function sendMessage() {
    const text = input.trim();
    if (!text) return;
    const userMsg = { role: "user", text, ts: Date.now() };

    // append user message
    setConversations(prev => {
      const copy = [...prev];
      copy[activeConvIndex] = {
        ...copy[activeConvIndex],
        messages: [...copy[activeConvIndex].messages, userMsg],
      };
      return copy;
    });
    setInput("");
    setIsSending(true);

    try {
      // call backend /api/chat (adjust payload if needed)
      const resp = await axios.post("http://localhost:5000/api/chat", { userId: "anon", message: text, countryCode: "IN" }, { timeout: 30000 });
      const botText = resp.data?.text ?? "Sorry — I couldn't reach the assistant.";

      const botMsg = { role: "bot", text: botText, ts: Date.now() };

      setConversations(prev => {
        const copy = [...prev];
        copy[activeConvIndex] = {
          ...copy[activeConvIndex],
          messages: [...copy[activeConvIndex].messages, botMsg],
        };
        return copy;
      });
    } catch (err) {
      console.error("chat send error", err);
      const errMsg = { role: "bot", text: "Something went wrong. Please try again.", ts: Date.now() };
      setConversations(prev => {
        const copy = [...prev];
        copy[activeConvIndex] = {
          ...copy[activeConvIndex],
          messages: [...copy[activeConvIndex].messages, errMsg],
        };
        return copy;
      });
    } finally {
      setIsSending(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  function renameActive(title) {
    setConversations(prev => {
      const copy = [...prev];
      copy[activeConvIndex] = { ...copy[activeConvIndex], title };
      return copy;
    });
  }

  function clearConversation(i) {
    setConversations(prev => {
      const copy = [...prev];
      copy[i] = { ...copy[i], messages: [] };
      return copy;
    });
  }

  return (
    <div className="chat-root">
      <aside className={`chat-sidebar ${sidebarOpen ? "open" : "closed"}`} aria-hidden={!sidebarOpen}>
        <div className="sidebar-top">
          <div className="sidebar-brand">
            <div className="logo-sm" aria-hidden>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="9" r="6" fill="#7C3AED" />
              </svg>
            </div>
            <div className="brand-text">
              <div className="brand-name">Empath</div>
              <div className="brand-sub">Confidant</div>
            </div>
          </div>

          <button className="new-chat-btn" onClick={newChat}>+ New chat</button>
        </div>

        <nav className="convs-list" role="navigation" aria-label="Conversations">
          {conversations.map((c, i) => (
            <div
              key={c.id}
              className={`conv-item ${i === activeConvIndex ? "active" : ""}`}
              onClick={() => selectChat(i)}
              title={c.title}
            >
              <div className="conv-title">{c.title || "Untitled"}</div>
              <div className="conv-actions">
                <button className="btn-ghost tiny" onClick={(e) => { e.stopPropagation(); clearConversation(i); }}>Clear</button>
              </div>
            </div>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <Link to="/" className="btn-ghost">Back to Home</Link>
          <button className="toggle-btn" onClick={() => setSidebarOpen(false)}>⟨</button>
        </div>
      </aside>

      <div className="chat-main">
        <header className="chat-main-header">
          <button className="hamburger" onClick={() => setSidebarOpen(s => !s)} aria-label="Toggle sidebar">
            ☰
          </button>

          <div className="conv-info">
            <input
              className="conv-title-input"
              value={activeConv.title}
              onChange={(e) => renameActive(e.target.value)}
              aria-label="Conversation title"
            />
            <div className="conv-meta muted">Private • AI Companion</div>
          </div>
        </header>

        <div ref={listRef} className="messages-list" role="log" aria-live="polite">
          {activeConv.messages.length === 0 && (
            <div className="empty-state">
              <h4>Say hello 👋</h4>
              <p>Start a conversation with Empath — it's private and non-diagnostic.</p>
            </div>
          )}

          {activeConv.messages.map((m, idx) => (
            <div key={idx} className={`message ${m.role === "user" ? "user" : "bot"}`}>
              <div className="message-bubble">
                <div className="message-text">{m.text}</div>
              </div>
            </div>
          ))}
        </div>

        <div className="composer">
          <textarea
            className="composer-input"
            placeholder="Type your message — press Enter to send"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
          />
          <div className="composer-actions">
            <button className="btn-ghost" onClick={() => { setInput(""); }}>Clear</button>
            <button className="btn-primary" onClick={sendMessage} disabled={isSending}>
              {isSending ? "Sending..." : "Send"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

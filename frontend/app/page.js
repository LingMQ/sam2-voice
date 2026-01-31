"use client";

import { useEffect, useMemo, useRef, useState } from "react";

function resolveWsUrl() {
  if (process.env.NEXT_PUBLIC_WS_URL) {
    return process.env.NEXT_PUBLIC_WS_URL;
  }

  if (typeof window === "undefined") {
    return "ws://localhost:8000/ws";
  }

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const { hostname, port } = window.location;

  if (port && port !== "8000") {
    return `${protocol}://${hostname}:8000/ws`;
  }

  return `${protocol}://${window.location.host}/ws`;
}

export default function Home() {
  const [status, setStatus] = useState("disconnected");
  const [transcript, setTranscript] = useState([]);
  const [events, setEvents] = useState([]);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const shouldReconnectRef = useRef(true);
  const wsUrl = useMemo(() => resolveWsUrl(), []);

  useEffect(() => {
    shouldReconnectRef.current = true;

    const connect = () => {
      setStatus("connecting");
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.addEventListener("open", () => {
        setStatus("connected");
      });

      ws.addEventListener("close", () => {
        setStatus("disconnected");
        if (shouldReconnectRef.current) {
          reconnectTimeoutRef.current = window.setTimeout(connect, 1500);
        }
      });

      ws.addEventListener("message", (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "text") {
            setTranscript((prev) => [
              ...prev,
              { role: "assistant", text: data.payload },
            ]);
          } else if (data.type === "status") {
            setEvents((prev) => [...prev, `status: ${data.payload}`]);
            setStatus(data.payload);
          } else if (data.type === "error") {
            setEvents((prev) => [...prev, `error: ${data.payload}`]);
          } else if (data.type === "turn_complete") {
            setEvents((prev) => [...prev, "turn complete"]);
          } else {
            setEvents((prev) => [...prev, JSON.stringify(data)]);
          }
        } catch (err) {
          setEvents((prev) => [...prev, `error: ${err.message}`]);
        }
      });
    };

    connect();

    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [wsUrl]);

  const connectedClass =
    status && status !== "disconnected" ? "connected" : "";
  const statusLabels = {
    disconnected: "Offline",
    connected: "Ready",
    starting: "Starting",
    ready: "Listening",
    stopping: "Stopping",
    stopped: "Paused",
    already_running: "Listening",
  };
  const statusLabel = statusLabels[status] || status;
  const micStatus = status === "ready" ? "Mic is on" : "Mic is off";
  const hasTranscript = transcript.length > 0;

  const sendAction = (action) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return;
    }
    ws.send(JSON.stringify({ action }));
  };

  return (
    <div className="page">
      <header className="topbar">
        <div className="brand">
          <div className="logo" aria-hidden="true">
            S2
          </div>
          <div className="brand-copy">
            <span className="brand-title">Sam2 Voice</span>
            <span className="brand-subtitle">Local conversational agent</span>
          </div>
        </div>
        <div className={`status-pill ${connectedClass}`}>
          <span className="dot" aria-hidden="true"></span>
          <span>{statusLabel}</span>
        </div>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <h1>A calm, supportive voice companion.</h1>
          <p className="note">
            Sam2 listens locally and responds in real time. Your microphone and
            speakers stay on this device.
          </p>
          <div className="controls">
            <button className="primary" onClick={() => sendAction("start")}>
              Start listening
            </button>
            <button
              onClick={() => sendAction("stop")}
              className="secondary"
            >
              Pause
            </button>
            <span className="status-note">{micStatus}</span>
          </div>
        </div>
        <div className="hero-card">
          <h2>How it helps</h2>
          <ul>
            <li>Break big tasks into small steps.</li>
            <li>Offer emotional support and grounding.</li>
            <li>Celebrate progress as you go.</li>
          </ul>
          <div className="privacy-card">
            <span className="privacy-title">Private by default</span>
            <span className="privacy-note">
              Audio never leaves this machine without your action.
            </span>
          </div>
        </div>
      </section>

      <section className="conversation">
        <div className="conversation-header">
          <div>
            <h2>Conversation</h2>
            <span className="muted">
              {transcript.length} message
              {transcript.length === 1 ? "" : "s"}
            </span>
          </div>
          <button
            className="ghost"
            onClick={() => setTranscript([])}
            type="button"
          >
            Clear conversation
          </button>
        </div>
        <div className="chat" aria-live="polite">
          {!hasTranscript && (
            <div className="empty-state">
              Press <strong>Start listening</strong>, then speak naturally.
            </div>
          )}
          {transcript.map((entry, index) => (
            <div className={`bubble ${entry.role}`} key={`${entry.text}-${index}`}>
              <span className="role">Assistant</span>
              <p>{entry.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="support-grid">
        <div className="support-card">
          <h3>Suggested prompts</h3>
          <div className="prompt-list">
            <span>I need help starting a task</span>
            <span>I feel overwhelmed right now</span>
            <span>Help me break this into steps</span>
          </div>
        </div>
        <div className="support-card">
          <h3>Daily check-in</h3>
          <p>
            Ask for a short check-in to reflect on what went well and what
            needs support today.
          </p>
        </div>
      </section>

      <details className="advanced">
        <summary>Advanced diagnostics</summary>
        <div className="panel">
          <div className="panel-header">
            <h2>Event log</h2>
            <button
              className="ghost"
              onClick={() => setEvents([])}
              type="button"
            >
              Clear
            </button>
          </div>
          <pre>{events.join("\n")}</pre>
        </div>
      </details>
    </div>
  );
}

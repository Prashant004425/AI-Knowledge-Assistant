"use client";

import { useState } from "react";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function HomePage() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const askQuestion = async (event) => {
    event.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError("");
    setAnswer("");
    setSources([]);

    try {
      const response = await axios.post(
        `${API_URL}/ask`,
        {
          question,
          n_retrieve: 5,
          temperature: 0.3,
        },
        {
          headers: {
            "Content-Type": "application/json",
          },
          timeout: 300000,
        }
      );

      setAnswer(response.data.answer || "No answer returned.");
      setSources(response.data.sources || []);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Request failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main style={{ padding: "2rem", fontFamily: "sans-serif", maxWidth: 900, margin: "0 auto" }}>
      <h1 style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>AI Knowledge Assistant</h1>
      <p style={{ marginBottom: "1.5rem", color: "#555" }}>
        Ask questions about your documents and see citations from the knowledge base.
      </p>

      <form onSubmit={askQuestion} style={{ display: "flex", gap: "0.75rem", marginBottom: "1rem" }}>
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="What is FloCard?"
          style={{ flex: 1, padding: "0.9rem", borderRadius: "0.75rem", border: "1px solid #ccc" }}
        />
        <button type="submit" disabled={loading} style={{ padding: "0.9rem 1.5rem", borderRadius: "0.75rem", border: "none", background: "#2563eb", color: "white" }}>
          {loading ? "Thinking..." : "Send"}
        </button>
      </form>

      {error && <div style={{ color: "#b91c1c", marginBottom: "1rem" }}>{error}</div>}

      {answer && (
        <section style={{ marginBottom: "1.5rem", padding: "1.25rem", border: "1px solid #e5e7eb", borderRadius: "0.75rem", background: "white" }}>
          <h2 style={{ marginBottom: "0.75rem" }}>AI Answer</h2>
          <p style={{ lineHeight: 1.7 }}>{answer}</p>
        </section>
      )}

      {sources.length > 0 && (
        <section style={{ padding: "1.25rem", border: "1px solid #e5e7eb", borderRadius: "0.75rem", background: "#f8fafc" }}>
          <h3 style={{ marginBottom: "0.75rem" }}>Sources</h3>
          <ul style={{ listStyle: "inside disc", lineHeight: 1.8 }}>
            {sources.map((source, index) => (
              <li key={index}>{source.source} ({Math.round((source.relevance || 0) * 100)}% relevance)</li>
            ))}
          </ul>
        </section>
      )}
    </main>

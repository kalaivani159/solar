import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import { useFetch } from "../hooks/useFetch";
import { useFilters } from "../state/filters";
import type { AssistantResponse } from "../types";

const SUGGESTIONS = [
  "Which locality has the highest total solar capacity?",
  "How much solar generation is available in Anna Nagar?",
  "Why does Anna Nagar have a high Solar Potential Index?",
  "How many rooftops have a payback below 7 years?",
  "What happens if the budget increases from ₹10 crore to ₹15 crore?",
  "What is the total potential capacity?",
  "Explain the solar potential of Velachery.",
  "What is the Solar Potential Index methodology?",
];

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  response?: AssistantResponse;
}

export default function Assistant() {
  const { emissionFactor } = useFilters();
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      text: "I am the SolarSphere AI planning assistant. I answer using the Feature 3 dataset, the analytics engine and the project knowledge base. Numbers are always calculated by the system — I never invent them.",
    },
  ]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const knowledge = useFetch(() => api.knowledge(), []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (question: string) => {
    const q = question.trim();
    if (!q || busy) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setBusy(true);
    try {
      const res = await api.ask(q, emissionFactor);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: res.answer, response: res },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: `Request failed: ${e instanceof Error ? e.message : String(e)}`,
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader
        title="AI Planning Assistant"
        subtitle="Grounded in the dataset, the analytics engine and the project documentation"
        right={
          <span className="badge badge-teal">
            {knowledge.data?.documents.length ?? 0} knowledge documents
          </span>
        }
      />
      <div className="content">
        <div className="split">
          <div className="card">
            <div className="card-title">Ask the planning assistant</div>
            <div className="card-sub">
              Numeric answers are computed first, then explained. Documentation questions use
              retrieval over the knowledge base.
            </div>

            <div className="chat-log">
              {messages.map((m, i) => (
                <div key={i} className={`msg ${m.role}`}>
                  {m.text}
                  {m.role === "assistant" && m.response && (
                    <div className="meta">
                      Mode: <b>{m.response.mode}</b> ·{" "}
                      {m.response.llm ? "language layer applied" : "deterministic explanation"}{" "}
                      · Sources:{" "}
                      {(m.response.sources ?? []).join(", ") || "project knowledge base"}
                    </div>
                  )}
                </div>
              ))}
              {busy && (
                <div className="msg assistant" style={{ display: "flex", gap: 9, alignItems: "center" }}>
                  <span className="spinner" style={{ borderTopColor: "#0f766e", borderColor: "#cbd5e1" }} />
                  Calculating from the dataset…
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
              <input
                type="text"
                value={input}
                placeholder="Ask about localities, capacity, generation, index, budget or methodology…"
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") send(input);
                }}
              />
              <button className="btn" onClick={() => send(input)} disabled={busy}>
                Ask
              </button>
            </div>

            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <span key={s} className="suggestion" onClick={() => send(s)}>
                  {s}
                </span>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="card-title">How answers are produced</div>
            <div className="card-sub">Two grounded pipelines, never free-form guessing</div>
            <div className="note">
              <b>Numeric questions</b>
              <br />
              User question → Feature 3 analytics engine → calculated result → explanation.
              The language layer may rephrase the answer but may not change any number.
            </div>
            <div className="note" style={{ marginTop: 10 }}>
              <b>Documentation questions</b>
              <br />
              User question → retrieval over the project knowledge base → retrieved source
              content → grounded response with the source filename shown.
            </div>

            <div className="card-title" style={{ marginTop: 18 }}>
              Knowledge base
            </div>
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Document</th>
                    <th>Title</th>
                    <th className="num">Chunks</th>
                  </tr>
                </thead>
                <tbody>
                  {(knowledge.data?.documents ?? []).map((d) => (
                    <tr key={d.filename}>
                      <td>{d.filename}</td>
                      <td>{d.title}</td>
                      <td className="num">{d.chunks}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="classification" style={{ marginTop: 12 }}>
              {knowledge.data?.answer_rule}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

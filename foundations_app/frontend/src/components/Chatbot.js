import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { motion, AnimatePresence } from "framer-motion";
import { MessageCircle, X, Send, Sparkles, Loader2, CheckCircle2 } from "lucide-react";

const API = `${import.meta.env.VITE_BACKEND_URL || "http://localhost:8000"}/api`;

const initialBot = {
  role: "assistant",
  content:
    "Hi, I'm Aria. I can help you find the right service — EAP, training, psychosocial risk, or organisational development. What's the workplace challenge on your mind?",
};

function getSessionId() {
  let id = localStorage.getItem("fca_chat_session");
  if (!id) {
    id = "s_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem("fca_chat_session", id);
  }
  return id;
}

export default function Chatbot() {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState("chat"); // chat | lead | done
  const [messages, setMessages] = useState([initialBot]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [lead, setLead] = useState({
    name: "",
    company: "",
    email: "",
    phone: "",
    inquiry_type: "",
  });
  const sessionId = useRef(getSessionId());
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, open, view]);

  const send = async (e) => {
    e?.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setBusy(true);
    try {
      const { data } = await axios.post(`${API}/chat/message`, {
        session_id: sessionId.current,
        message: text,
      });
      setMessages((m) => [...m, { role: "assistant", content: data.reply }]);
    } catch {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content:
            "I'm having trouble reaching the network. Please try again, or share your details and we'll follow up.",
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const submitLead = async (e) => {
    e.preventDefault();
    if (!lead.email || !lead.name) return;
    setBusy(true);
    try {
      await axios.post(`${API}/chat/lead`, {
        ...lead,
        session_id: sessionId.current,
        notes: messages
          .slice(-6)
          .map((m) => `${m.role}: ${m.content}`)
          .join("\n"),
      });
      setView("done");
    } catch {
      setView("done");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <motion.button
        data-testid="chatbot-toggle"
        aria-label="Open chat"
        onClick={() => setOpen((o) => !o)}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-[#4C1D95] text-white shadow-[0_12px_32px_-8px_rgba(28,63,58,0.55)] flex items-center justify-center"
      >
        <AnimatePresence mode="wait">
          {open ? (
            <motion.span
              key="x"
              initial={{ rotate: -90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: 90, opacity: 0 }}
            >
              <X size={22} />
            </motion.span>
          ) : (
            <motion.span
              key="msg"
              initial={{ rotate: 90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: -90, opacity: 0 }}
            >
              <MessageCircle size={22} />
            </motion.span>
          )}
        </AnimatePresence>
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            data-testid="chatbot-panel"
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ type: "spring", stiffness: 320, damping: 28 }}
            className="fixed bottom-24 right-6 z-50 w-[min(92vw,380px)] h-[560px] bg-white rounded-2xl border border-slate-200 shadow-[0_30px_60px_-15px_rgba(0,0,0,0.18)] flex flex-col overflow-hidden"
          >
            <div className="px-5 py-4 bg-[#4C1D95] text-white flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-[#D4A373] flex items-center justify-center text-[#4C1D95]">
                <Sparkles size={16} />
              </div>
              <div>
                <p className="text-sm font-medium leading-none">Aria</p>
                <p className="text-[11px] text-white/70 mt-1">
                  Foundations Counselling Academy
                </p>
              </div>
              <div className="ml-auto flex gap-2">
                <button
                  data-testid="chatbot-leadview"
                  onClick={() => setView(view === "lead" ? "chat" : "lead")}
                  className="text-[11px] px-3 py-1 rounded-full bg-white/10 hover:bg-white/20"
                >
                  {view === "lead" ? "Back to chat" : "Talk to a human"}
                </button>
              </div>
            </div>

            {view === "chat" && (
              <>
                <div
                  ref={scrollRef}
                  className="flex-1 overflow-y-auto px-4 py-5 space-y-3 bg-[#FAFAFA]"
                >
                  {messages.map((m, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`max-w-[85%] text-sm rounded-2xl px-4 py-2.5 leading-relaxed ${
                        m.role === "user"
                          ? "ml-auto bg-[#4C1D95] text-white"
                          : "bg-white border border-slate-100 text-[#0F172A]"
                      }`}
                    >
                      {m.content}
                    </motion.div>
                  ))}
                  {busy && (
                    <div className="bg-white border border-slate-100 rounded-2xl px-4 py-2.5 inline-flex items-center gap-2 text-sm text-[#475569]">
                      <Loader2 size={14} className="animate-spin" />
                      Aria is typing…
                    </div>
                  )}
                </div>
                <form
                  onSubmit={send}
                  className="border-t border-slate-100 px-3 py-3 flex items-center gap-2 bg-white"
                >
                  <input
                    data-testid="chatbot-input"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask about services, EAP, training…"
                    className="flex-1 text-sm px-3 py-2 rounded-full bg-[#F1F5F2] outline-none focus:ring-2 ring-[#4C1D95]/20"
                  />
                  <button
                    data-testid="chatbot-send"
                    type="submit"
                    disabled={busy || !input.trim()}
                    className="w-9 h-9 rounded-full bg-[#4C1D95] text-white flex items-center justify-center disabled:opacity-50"
                  >
                    <Send size={15} />
                  </button>
                </form>
              </>
            )}

            {view === "lead" && (
              <form
                onSubmit={submitLead}
                className="flex-1 overflow-y-auto p-5 space-y-3 bg-[#FAFAFA]"
              >
                <p className="text-sm text-[#475569]">
                  Share a few details and we'll be in touch within one business day.
                </p>
                {[
                  ["name", "Full name"],
                  ["company", "Company"],
                  ["email", "Work email"],
                  ["phone", "Phone (optional)"],
                ].map(([k, label]) => (
                  <input
                    key={k}
                    data-testid={`chatbot-lead-${k}`}
                    required={k === "name" || k === "email"}
                    type={k === "email" ? "email" : "text"}
                    value={lead[k]}
                    onChange={(e) => setLead({ ...lead, [k]: e.target.value })}
                    placeholder={label}
                    className="w-full text-sm px-4 py-2.5 rounded-lg bg-white border border-slate-200 outline-none focus:ring-2 ring-[#4C1D95]/20"
                  />
                ))}
                <select
                  data-testid="chatbot-lead-inquiry"
                  value={lead.inquiry_type}
                  onChange={(e) =>
                    setLead({ ...lead, inquiry_type: e.target.value })
                  }
                  className="w-full text-sm px-4 py-2.5 rounded-lg bg-white border border-slate-200 outline-none"
                >
                  <option value="">Inquiry type…</option>
                  <option>EAP & Counselling</option>
                  <option>Corporate Training</option>
                  <option>Psychosocial Risk Management</option>
                  <option>Organisational Development</option>
                  <option>Other</option>
                </select>
                <button
                  data-testid="chatbot-lead-submit"
                  type="submit"
                  disabled={busy}
                  className="btn-primary w-full justify-center"
                >
                  {busy ? "Sending…" : "Request follow-up"}
                </button>
              </form>
            )}

            {view === "done" && (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-[#FAFAFA]">
                <CheckCircle2 size={42} className="text-[#81B29A] mb-4" />
                <p className="text-base font-medium text-[#0F172A]">
                  Thank you, {lead.name.split(" ")[0] || "there"}.
                </p>
                <p className="text-sm text-[#475569] mt-2 max-w-xs">
                  A consultant will reach out shortly. You can keep the chat open if
                  you have more questions.
                </p>
                <button
                  data-testid="chatbot-back"
                  onClick={() => setView("chat")}
                  className="mt-6 btn-ghost text-sm"
                >
                  Back to chat
                </button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

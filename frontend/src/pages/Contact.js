import { useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Mail, Phone, MapPin, Send, Loader2, CheckCircle2 } from "lucide-react";
import Reveal from "@/components/Reveal";
import SectionHeading from "@/components/SectionHeading";
import { SITE } from "@/data/site";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Contact() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    company: "",
    phone: "",
    inquiry_type: "",
    message: "",
  });
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const update = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    if (!form.name || !form.email || !form.message) {
      toast.error("Please fill name, email and message.");
      return;
    }
    setBusy(true);
    try {
      await axios.post(`${API}/contact`, form);
      setDone(true);
      toast.success("Thanks — we'll be in touch within one business day.");
    } catch {
      toast.error("Something went wrong. Please try again or email us directly.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <section className="section pt-16">
        <div className="container-x">
          <SectionHeading
            eyebrow="Contact"
            title="Tell us what's happening at work. We'll listen."
            description="Use the form, the chatbot, email or phone — whichever feels right. We respond within one business day."
            testid="contact-heading"
          />
        </div>
      </section>

      <section className="container-x">
        <div className="grid md:grid-cols-12 gap-10">
          <div className="md:col-span-7">
            <Reveal>
              {done ? (
                <div
                  data-testid="contact-success"
                  className="bg-[#F1F5F2] rounded-2xl p-12 text-center"
                >
                  <CheckCircle2
                    size={48}
                    className="text-[#81B29A] mx-auto"
                  />
                  <h3 className="mt-6 text-2xl font-semibold text-[#0F172A]">
                    Message received.
                  </h3>
                  <p className="mt-3 text-[#475569] max-w-md mx-auto">
                    Thank you, {form.name.split(" ")[0]}. A consultant will reach
                    out at <span className="font-medium">{form.email}</span> within
                    one business day.
                  </p>
                </div>
              ) : (
                <form
                  data-testid="contact-form"
                  onSubmit={submit}
                  className="bg-white border border-slate-100 rounded-2xl p-8 md:p-10 space-y-5"
                >
                  <div className="grid md:grid-cols-2 gap-4">
                    <Field
                      id="name"
                      label="Full name"
                      value={form.name}
                      onChange={update("name")}
                      required
                    />
                    <Field
                      id="email"
                      type="email"
                      label="Work email"
                      value={form.email}
                      onChange={update("email")}
                      required
                    />
                  </div>
                  <div className="grid md:grid-cols-2 gap-4">
                    <Field
                      id="company"
                      label="Company"
                      value={form.company}
                      onChange={update("company")}
                    />
                    <Field
                      id="phone"
                      label="Phone (optional)"
                      value={form.phone}
                      onChange={update("phone")}
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="inquiry_type"
                      className="text-xs uppercase tracking-[0.2em] text-[#475569]"
                    >
                      Inquiry type
                    </label>
                    <select
                      id="inquiry_type"
                      data-testid="contact-inquiry"
                      value={form.inquiry_type}
                      onChange={update("inquiry_type")}
                      className="mt-2 w-full px-4 py-3 rounded-lg bg-[#FAFAFA] border border-slate-200 outline-none focus:ring-2 ring-[#1C3F3A]/20"
                    >
                      <option value="">Choose…</option>
                      <option>EAP & Counselling</option>
                      <option>Corporate Training</option>
                      <option>Psychosocial Risk Management</option>
                      <option>Organisational Development</option>
                      <option>General enquiry</option>
                    </select>
                  </div>

                  <div>
                    <label
                      htmlFor="message"
                      className="text-xs uppercase tracking-[0.2em] text-[#475569]"
                    >
                      Message *
                    </label>
                    <textarea
                      id="message"
                      data-testid="contact-message"
                      required
                      rows={5}
                      value={form.message}
                      onChange={update("message")}
                      className="mt-2 w-full px-4 py-3 rounded-lg bg-[#FAFAFA] border border-slate-200 outline-none focus:ring-2 ring-[#1C3F3A]/20 resize-none"
                      placeholder="Tell us a little about your team, the challenge, and what you'd like to achieve."
                    />
                  </div>

                  <button
                    type="submit"
                    data-testid="contact-submit"
                    disabled={busy}
                    className="btn-primary w-full md:w-auto justify-center"
                  >
                    {busy ? (
                      <>
                        <Loader2 size={16} className="animate-spin" />
                        Sending…
                      </>
                    ) : (
                      <>
                        Send enquiry
                        <Send size={16} />
                      </>
                    )}
                  </button>
                </form>
              )}
            </Reveal>
          </div>

          <div className="md:col-span-5 space-y-4">
            <Reveal delay={0.05}>
              <div className="bg-[#1C3F3A] text-white rounded-2xl p-8">
                <p className="eyebrow text-[#D4A373]">Office</p>
                <h3 className="mt-3 text-2xl font-semibold">{SITE.name}</h3>
                <p className="mt-2 text-white/70 text-sm">{SITE.parent}</p>

                <div className="mt-8 space-y-4 text-sm">
                  <a
                    href={`mailto:${SITE.email}`}
                    data-testid="contact-email"
                    className="flex items-start gap-3 hover:text-[#D4A373]"
                  >
                    <Mail size={18} className="text-[#D4A373] mt-0.5" />
                    {SITE.email}
                  </a>
                  <a
                    href={`tel:${SITE.phone.replace(/\s+/g, "")}`}
                    data-testid="contact-phone"
                    className="flex items-start gap-3 hover:text-[#D4A373]"
                  >
                    <Phone size={18} className="text-[#D4A373] mt-0.5" />
                    {SITE.phone}
                  </a>
                  <p className="flex items-start gap-3">
                    <MapPin size={18} className="text-[#D4A373] mt-0.5" />
                    <span>
                      {SITE.address}
                      <br />
                      <span className="text-white/60">{SITE.hours}</span>
                    </span>
                  </p>
                </div>
              </div>
            </Reveal>
            <Reveal delay={0.1}>
              <div className="bg-[#F1F5F2] rounded-2xl p-8 border border-[#E2E8F0]">
                <p className="eyebrow">Prefer to chat?</p>
                <p className="mt-3 text-[#0F172A] font-medium">
                  Aria, our assistant, is in the bottom-right corner.
                </p>
                <p className="mt-2 text-sm text-[#475569]">
                  She can answer service questions and pass you to a human within
                  the same conversation.
                </p>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      <div className="h-24" />
    </>
  );
}

function Field({ id, label, value, onChange, type = "text", required }) {
  return (
    <div>
      <label
        htmlFor={id}
        className="text-xs uppercase tracking-[0.2em] text-[#475569]"
      >
        {label}
        {required && " *"}
      </label>
      <input
        id={id}
        data-testid={`contact-${id}`}
        type={type}
        value={value}
        onChange={onChange}
        required={required}
        className="mt-2 w-full px-4 py-3 rounded-lg bg-[#FAFAFA] border border-slate-200 outline-none focus:ring-2 ring-[#1C3F3A]/20"
      />
    </div>
  );
}

import { useState } from "react";
import { ShieldCheck, Users, BarChart3, Clock, CheckCircle2, ArrowRight, Building, Mail, Phone, MessageSquare } from "lucide-react";
import SectionHeading from "@/components/SectionHeading";
import SEO from "@/components/SEO";
import { SITE, getWhatsAppUrl } from "@/data/site";

export default function CorporateWellness() {
  const [formData, setFormData] = useState({
    name: "",
    organisation: "",
    role: "",
    email: "",
    phone: "",
    staff_size: "10-50 employees",
    service_interest: "Full EAP & Counselling",
    contact_method: "Email",
    needs_summary: ""
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMsg("");

    const payload = {
      name: formData.name,
      email: formData.email,
      company: formData.organisation,
      phone: formData.phone,
      inquiry_type: `Corporate: ${formData.service_interest} (${formData.staff_size})`,
      message: `Role: ${formData.role} | Preferred Contact: ${formData.contact_method} | Needs: ${formData.needs_summary}`
    };

    try {
      const res = await fetch("https://foundations-api-aq7k.onrender.com/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        setIsSubmitted(true);
      } else {
        throw new Error("Failed to submit corporate consultation request. Please contact us directly.");
      }
    } catch (err) {
      setErrorMsg(err.message || "An error occurred. Please reach out via email or phone.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <SEO
        title="Corporate Wellness, EAP & Psychosocial Risk"
        description="Comprehensive Employee Assistance Programmes (EAP), ISO 45003 workplace risk mapping, and executive wellness reporting for organisations in Botswana."
        path="/corporate-wellness"
      />

      {/* Hero */}
      <section className="section bg-[#1C3F3A] text-white pt-16 pb-20 border-b border-[#15302C]">
        <div className="container-x grid lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-8 space-y-6">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/10 text-xs font-semibold uppercase tracking-wider text-[#D4A373]">
              <ShieldCheck size={14} />
              <span>B2B Workplace Mental Health & EAP</span>
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.08]">
              Healthy people. <span className="text-[#D4A373]">Sustainable performance.</span>
            </h1>
            <p className="text-lg text-white/80 max-w-2xl leading-relaxed">
              We partner with executives, HR directors, and People & Culture leaders to manage psychosocial risk, reduce burnout, provide 24/7 EAP support, and deliver board-level utilization analytics.
            </p>
            <div className="flex flex-wrap gap-4 pt-2">
              <a
                href="#consultation-form"
                data-testid="corporate-hero-consult-btn"
                className="inline-flex items-center gap-2 px-8 py-4 rounded-full bg-[#D4A373] text-[#1C3F3A] font-bold text-sm hover:bg-white transition-all shadow-lg"
              >
                <span>Request a Consultation</span>
                <ArrowRight size={16} />
              </a>
              <a
                href={getWhatsAppUrl("corporate")}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-7 py-4 rounded-full bg-white/10 hover:bg-white/20 text-white font-semibold text-sm transition-all border border-white/20"
              >
                <span>Discuss on WhatsApp</span>
              </a>
            </div>
          </div>

          <div className="lg:col-span-4 bg-white/5 border border-white/10 rounded-3xl p-8 space-y-4">
            <p className="text-xs uppercase tracking-widest text-[#D4A373] font-bold">Why Partner With FCA</p>
            <ul className="space-y-3 text-sm text-white/85">
              <li className="flex items-start gap-2.5">
                <CheckCircle2 size={16} className="text-[#D4A373] flex-shrink-0 mt-0.5" />
                <span><strong>ISO 45003 Compliance:</strong> Benchmark and mitigate psychosocial hazards.</span>
              </li>
              <li className="flex items-start gap-2.5">
                <CheckCircle2 size={16} className="text-[#D4A373] flex-shrink-0 mt-0.5" />
                <span><strong>24/7 EAP Access:</strong> Confidential support for staff and dependants.</span>
              </li>
              <li className="flex items-start gap-2.5">
                <CheckCircle2 size={16} className="text-[#D4A373] flex-shrink-0 mt-0.5" />
                <span><strong>Board-Level Dashboards:</strong> Anonymised quarterly utilisation reporting.</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* Corporate Pillars */}
      <section className="section bg-white">
        <div className="container-x">
          <SectionHeading
            eyebrow="Enterprise Capabilities"
            title="Comprehensive workplace wellbeing solutions."
            description="From preventative hazard audits to crisis debriefing, we provide end-to-end organizational support."
          />

          <div className="mt-12 grid md:grid-cols-3 gap-8">
            <div className="p-8 rounded-2xl bg-[#FAFAFA] border border-slate-200 space-y-4">
              <ShieldCheck size={28} className="text-[#1C3F3A]" />
              <h3 className="text-xl font-bold text-[#0F172A]">Employee Assistance (EAP)</h3>
              <p className="text-sm text-[#475569] leading-relaxed">
                Full-service employee counselling covering personal distress, work conflicts, trauma debriefing, and financial stress signposting.
              </p>
            </div>

            <div className="p-8 rounded-2xl bg-[#FAFAFA] border border-slate-200 space-y-4">
              <BarChart3 size={28} className="text-[#1C3F3A]" />
              <h3 className="text-xl font-bold text-[#0F172A]">Psychosocial Risk Audits</h3>
              <p className="text-sm text-[#475569] leading-relaxed">
                Structured assessments evaluating job demands, organisational support, and workplace culture aligned with the ISO 45003 standard.
              </p>
            </div>

            <div className="p-8 rounded-2xl bg-[#FAFAFA] border border-slate-200 space-y-4">
              <Users size={28} className="text-[#1C3F3A]" />
              <h3 className="text-xl font-bold text-[#0F172A]">Leader & Manager Coaching</h3>
              <p className="text-sm text-[#475569] leading-relaxed">
                Empower line managers with emotional intelligence and psychological safety tools to spot early distress signals in teams.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* B2B Consultation Form */}
      <section id="consultation-form" className="section bg-[#F1F5F2]" data-testid="corporate-form-section">
        <div className="container-x max-w-4xl bg-white rounded-3xl p-8 sm:p-12 border border-slate-200 shadow-sm">
          <div className="text-center space-y-2 mb-8">
            <p className="eyebrow">Enterprise Enquiry</p>
            <h2 className="text-3xl font-bold text-[#0F172A]">Request a Corporate Consultation</h2>
            <p className="text-sm text-[#475569]">Share your team's context and an FCA practice lead will contact you with a tailored proposal.</p>
          </div>

          {isSubmitted ? (
            <div className="p-8 rounded-2xl bg-[#F1F5F2] text-center space-y-4">
              <CheckCircle2 size={48} className="mx-auto text-[#1C3F3A]" />
              <h3 className="text-2xl font-bold text-[#0F172A]">Thank you for your enquiry</h3>
              <p className="text-sm text-[#475569] max-w-md mx-auto">
                Your consultation request has been received. An FCA corporate specialist will reach out within 24 business hours.
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-6">
              {errorMsg && (
                <div className="p-4 rounded-xl bg-red-50 text-red-700 text-sm border border-red-200">
                  {errorMsg}
                </div>
              )}

              <div className="grid sm:grid-cols-2 gap-6">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-[#0F172A] mb-2">
                    Full Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:border-[#1C3F3A] text-sm"
                    placeholder="e.g. Kagiso Motsepe"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-[#0F172A] mb-2">
                    Organisation Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.organisation}
                    onChange={(e) => setFormData({ ...formData, organisation: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:border-[#1C3F3A] text-sm"
                    placeholder="e.g. Standard Bank Botswana"
                  />
                </div>
              </div>

              <div className="grid sm:grid-cols-2 gap-6">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-[#0F172A] mb-2">
                    Your Role / Job Title *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:border-[#1C3F3A] text-sm"
                    placeholder="e.g. Head of HR / People Lead"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-[#0F172A] mb-2">
                    Work Email *
                  </label>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:border-[#1C3F3A] text-sm"
                    placeholder="name@company.com"
                  />
                </div>
              </div>

              <div className="grid sm:grid-cols-3 gap-6">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-[#0F172A] mb-2">
                    Phone Number
                  </label>
                  <input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:border-[#1C3F3A] text-sm"
                    placeholder="+267 ..."
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-[#0F172A] mb-2">
                    Estimated Staff Size
                  </label>
                  <select
                    value={formData.staff_size}
                    onChange={(e) => setFormData({ ...formData, staff_size: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:border-[#1C3F3A] text-sm bg-white"
                  >
                    <option>Under 10 employees</option>
                    <option>10-50 employees</option>
                    <option>50-250 employees</option>
                    <option>250-1000 employees</option>
                    <option>1000+ employees</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-[#0F172A] mb-2">
                    Service of Interest
                  </label>
                  <select
                    value={formData.service_interest}
                    onChange={(e) => setFormData({ ...formData, service_interest: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:border-[#1C3F3A] text-sm bg-white"
                  >
                    <option>Full EAP & Counselling</option>
                    <option>ISO 45003 Psychosocial Risk Audit</option>
                    <option>Executive / Leadership Coaching</option>
                    <option>Critical Incident Debriefing</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-[#0F172A] mb-2">
                  Summary of Needs / Goals
                </label>
                <textarea
                  rows={4}
                  value={formData.needs_summary}
                  onChange={(e) => setFormData({ ...formData, needs_summary: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:border-[#1C3F3A] text-sm"
                  placeholder="Briefly describe what your organisation is looking to achieve..."
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-4 rounded-full bg-[#1C3F3A] text-white font-bold text-sm hover:bg-[#15302C] transition-colors shadow-md disabled:opacity-50"
              >
                {isSubmitting ? "Transmitting Enquiry..." : "Submit Consultation Request"}
              </button>
            </form>
          )}
        </div>
      </section>
    </>
  );
}

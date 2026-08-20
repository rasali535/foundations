import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowUpRight,
  ShieldCheck,
  HeartPulse,
  Users,
  GraduationCap,
  Sparkles,
  ArrowRight,
  CheckCircle2,
  Phone,
  MessageCircle,
  Clock,
  Compass,
  FileText
} from "lucide-react";

import Reveal from "@/components/Reveal";
import Counter from "@/components/Counter";
import SectionHeading from "@/components/SectionHeading";
import CTABanner from "@/components/CTABanner";
import SEO from "@/components/SEO";
import {
  CORE_PATHWAYS,
  FEATURED_OFFER,
  HOW_IT_WORKS_STEPS,
  METRICS,
  SITE,
  getWhatsAppUrl
} from "@/data/site";

const PATHWAY_ICONS = {
  counselling: HeartPulse,
  "corporate-wellness": ShieldCheck,
  "training-team-building": Users,
  "online-programmes": GraduationCap,
};

export default function Home() {
  return (
    <>
      <SEO 
        title="Foundations Counselling Academy" 
        description="Practical mental wellness support for people, teams and organisations. Counselling, workplace wellness, corporate training and online programmes from Gaborone, Botswana."
        path="/"
      />

      {/* SECTION 1 — HERO */}
      <section
        data-testid="home-hero"
        className="relative min-h-[90vh] flex items-center overflow-hidden bg-[#FAFAFA] pt-12 pb-20"
      >
        <div className="absolute inset-0 bg-gradient-to-b from-[#F1F5F2]/80 via-white to-[#FAFAFA]" />
        <div className="grain opacity-15" />

        <div className="relative container-x grid lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-8 space-y-6">
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.6 }}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#1C3F3A]/5 border border-[#1C3F3A]/10 text-xs font-semibold uppercase tracking-widest text-[#1C3F3A]"
            >
              <span className="w-2 h-2 rounded-full bg-[#D4A373] animate-pulse" />
              <span>Gaborone, Botswana · {SITE.parent}</span>
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.7 }}
              className="text-4xl sm:text-5xl lg:text-7xl font-bold tracking-tight leading-[1.04] text-[#0F172A]"
            >
              Practical mental wellness support for{" "}
              <span className="italic text-[#1C3F3A]">people, teams</span> and{" "}
              <span className="text-[#D4A373]">organisations.</span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35, duration: 0.7 }}
              className="text-lg sm:text-xl text-[#475569] max-w-2xl leading-relaxed"
            >
              Counselling, workplace wellness, accredited training and practical online programmes from Gaborone to wherever you are.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.7 }}
              className="pt-4 flex flex-wrap gap-4 items-center"
            >
              <Link
                to="/counselling"
                data-testid="hero-cta-primary"
                className="btn-primary flex items-center gap-2 shadow-md hover:shadow-lg transition-all"
              >
                <span>Get Support</span>
                <ArrowRight size={18} />
              </Link>
              <Link
                to="/corporate-wellness"
                data-testid="hero-cta-secondary"
                className="inline-flex items-center gap-2 px-7 py-3.5 rounded-full text-[#1C3F3A] bg-white border border-slate-200 hover:border-[#1C3F3A] hover:bg-[#F1F5F2] font-semibold text-sm transition-all"
              >
                <span>Explore Corporate Services</span>
                <ArrowUpRight size={16} />
              </Link>
            </motion.div>

            {/* Micro reassurance badges */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.65, duration: 0.7 }}
              className="pt-6 grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs text-[#475569] border-t border-slate-200/60"
            >
              <span className="flex items-center gap-1.5">
                <CheckCircle2 size={14} className="text-[#81B29A]" />
                100% Confidential
              </span>
              <span className="flex items-center gap-1.5">
                <CheckCircle2 size={14} className="text-[#81B29A]" />
                In-Person & Virtual
              </span>
              <span className="flex items-center gap-1.5">
                <CheckCircle2 size={14} className="text-[#81B29A]" />
                ISO 45003 Aligned
              </span>
            </motion.div>
          </div>

          <div className="lg:col-span-4 hidden lg:block">
            <div className="relative rounded-3xl overflow-hidden border border-slate-100 shadow-2xl bg-[#1C3F3A] p-8 text-white">
              <div className="absolute top-0 right-0 w-48 h-48 bg-[#81B29A]/10 rounded-full blur-2xl" />
              <p className="eyebrow text-[#D4A373]">One Connected Ecosystem</p>
              <h2 className="text-2xl font-bold mt-2 leading-snug">
                How can FCA help you today?
              </h2>
              <p className="mt-3 text-sm text-white/75 leading-relaxed">
                Whether you need individual therapy, an enterprise EAP, team building, or online leadership masterclasses, our structured pathways make your next step clear.
              </p>
              <div className="mt-6 pt-6 border-t border-white/10 space-y-3 text-xs">
                <Link to="/counselling" className="flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors">
                  <span>Looking for Personal Therapy</span>
                  <ArrowRight size={14} className="text-[#D4A373]" />
                </Link>
                <Link to="/corporate-wellness" className="flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors">
                  <span>Looking for Corporate Wellness</span>
                  <ArrowRight size={14} className="text-[#D4A373]" />
                </Link>
                <Link to="/training-team-building" className="flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors">
                  <span>Looking for Team Training</span>
                  <ArrowRight size={14} className="text-[#D4A373]" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 2 — THE 4 CORE SERVICE PATHWAY CARDS */}
      <section className="section bg-white border-y border-slate-100" data-testid="service-pathways">
        <div className="container-x">
          <SectionHeading
            eyebrow="Core Service Pathways"
            title="Four connected service lines designed for sustainable human performance."
            description="Choose the pathway suited to you, your team, or your entire organisation."
            center
          />

          <div className="mt-14 grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {CORE_PATHWAYS.map((p, idx) => {
              const Icon = PATHWAY_ICONS[p.slug] || HeartPulse;
              return (
                <Reveal key={p.slug} delay={idx * 0.08}>
                  <div className="bg-[#FAFAFA] border border-slate-200/80 rounded-2xl p-7 h-full flex flex-col justify-between hover:shadow-lg hover:border-[#1C3F3A]/40 transition-all group">
                    <div className="space-y-4">
                      <div
                        className="w-12 h-12 rounded-xl flex items-center justify-center text-white shadow-sm"
                        style={{ backgroundColor: p.accent }}
                      >
                        <Icon size={22} />
                      </div>
                      <span className="text-[11px] font-bold uppercase tracking-widest text-[#475569]">
                        {p.eyebrow}
                      </span>
                      <h3 className="text-xl font-bold text-[#0F172A] group-hover:text-[#1C3F3A] transition-colors">
                        {p.title}
                      </h3>
                      <p className="text-xs font-semibold text-[#1C3F3A]">
                        {p.headline}
                      </p>
                      <p className="text-sm text-[#475569] leading-relaxed">
                        {p.description}
                      </p>
                    </div>

                    <div className="pt-6 mt-6 border-t border-slate-200/60 flex items-center justify-between">
                      <Link
                        to={p.to}
                        className="text-xs font-bold text-[#1C3F3A] inline-flex items-center gap-1.5 group-hover:underline"
                      >
                        <span>{p.cta}</span>
                        <ArrowUpRight size={14} />
                      </Link>
                      <span className="text-[10px] text-slate-400 font-medium">
                        0{idx + 1}
                      </span>
                    </div>
                  </div>
                </Reveal>
              );
            })}
          </div>
        </div>
      </section>

      {/* SECTION 3 — TRUST & CREDIBILITY */}
      <section className="section bg-[#F1F5F2]" data-testid="trust-section">
        <div className="container-x grid lg:grid-cols-12 gap-10 items-center">
          <div className="lg:col-span-6 space-y-5">
            <p className="eyebrow">Trust & Experience</p>
            <h2 className="text-3xl sm:text-4xl font-bold text-[#0F172A] leading-tight">
              Rooted in Gaborone. Delivering evidence-led behavioural care.
            </h2>
            <p className="text-base text-[#475569] leading-relaxed">
              Foundations Counselling Academy (FCA) bridges clinical mental health, workplace organisational health, and accredited professional development under one unified standard of practice.
            </p>
            <ul className="space-y-3 pt-2 text-sm text-[#0F172A]">
              <li className="flex items-start gap-2.5">
                <CheckCircle2 size={18} className="text-[#1C3F3A] flex-shrink-0 mt-0.5" />
                <span><strong>Physical Base in Gaborone:</strong> In-person consultations conducted at Plot 18680 Khuhurutse St, Phase 2.</span>
              </li>
              <li className="flex items-start gap-2.5">
                <CheckCircle2 size={18} className="text-[#1C3F3A] flex-shrink-0 mt-0.5" />
                <span><strong>Multi-Modal Delivery:</strong> Face-to-face counselling, secure virtual therapy, on-site corporate workshops, and online learning.</span>
              </li>
              <li className="flex items-start gap-2.5">
                <CheckCircle2 size={18} className="text-[#1C3F3A] flex-shrink-0 mt-0.5" />
                <span><strong>Governed Practice:</strong> Board-certified psychologists, experienced facilitators, and strict clinical confidentiality.</span>
              </li>
            </ul>
          </div>

          <div className="lg:col-span-6 grid grid-cols-2 gap-4">
            {METRICS.map((m, i) => (
              <div key={m.label} className="bg-white rounded-2xl p-6 border border-slate-100 text-center shadow-sm">
                <p className="text-4xl font-extrabold text-[#1C3F3A]">
                  <Counter target={m.value} />
                  <span className="text-[#D4A373]">{m.suffix}</span>
                </p>
                <p className="mt-2 text-xs font-semibold uppercase tracking-wider text-[#475569]">
                  {m.label}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SECTION 4 — FEATURED COUNSELLING SPOTLIGHT */}
      <section className="section bg-white" data-testid="counselling-spotlight">
        <div className="container-x grid lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-6 space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#81B29A]/15 text-xs font-semibold text-[#1C3F3A]">
              <HeartPulse size={14} />
              <span>Personal & Couples Counselling</span>
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold text-[#0F172A] leading-tight">
              A private, compassionate space to navigate life's challenges.
            </h2>
            <p className="text-base text-[#475569] leading-relaxed">
              We provide warm, respectful, and non-stigmatising therapy for individuals, couples, and families. Whether dealing with anxiety, relationship strain, burnout, or bereavement, our experienced counsellors offer structured, practical support.
            </p>
            <div className="p-5 rounded-2xl bg-[#FAFAFA] border border-slate-200/80 space-y-2 text-sm text-[#475569]">
              <p className="flex items-center gap-2 text-[#0F172A] font-semibold">
                <Clock size={16} className="text-[#D4A373]" />
                <span>50–60 Minute Structured Sessions</span>
              </p>
              <p>In-person sessions in Phase 2, Gaborone or confidential virtual appointments.</p>
              <p className="text-xs text-[#81B29A] font-medium pt-1">
                *Counselling rates are discussed confidentially with FCA coordinators upon initial enquiry.
              </p>
            </div>
            <div className="flex flex-wrap gap-4 pt-2">
              <a
                href={getWhatsAppUrl("counselling")}
                target="_blank"
                rel="noopener noreferrer"
                data-testid="counselling-whatsapp-btn"
                className="btn-primary flex items-center gap-2"
              >
                <MessageCircle size={18} />
                <span>Enquire on WhatsApp</span>
              </a>
              <a
                href={`tel:${SITE.phone.replace(/\s+/g, "")}`}
                className="btn-ghost flex items-center gap-2"
              >
                <Phone size={16} />
                <span>Call {SITE.phone}</span>
              </a>
            </div>
          </div>

          <div className="lg:col-span-6">
            <div className="relative rounded-3xl overflow-hidden shadow-xl border border-slate-100">
              <img
                src="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxOTB8MHwxfHNlYXJjaHwxfHxjb3Vuc2VsbGluZyUyMHNlc3Npb258ZW58MHx8fHwxNzc3MjE2NzEwfDA&ixlib=rb-4.1.0&q=85"
                alt="FCA Counselling Session"
                className="w-full h-80 sm:h-96 object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent flex items-end p-8 text-white">
                <div>
                  <p className="text-xs uppercase tracking-widest text-[#D4A373] font-semibold">Safe & Confidential</p>
                  <p className="text-lg font-medium mt-1">Every session is held under strict professional ethics.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 5 — CORPORATE WELLNESS & EAP SPOTLIGHT */}
      <section className="section bg-[#1C3F3A] text-white" data-testid="corporate-spotlight">
        <div className="container-x grid lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-6 space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-xs font-semibold text-[#D4A373]">
              <ShieldCheck size={14} />
              <span>B2B Workplace Wellness & EAP</span>
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold leading-tight">
              Healthy people. <span className="text-[#D4A373]">Sustainable performance.</span>
            </h2>
            <p className="text-base text-white/80 leading-relaxed">
              We partner with executives, HR, and People & Culture leaders to implement ISO 45003 aligned psychosocial hazard mapping, 24/7 crisis support, employee counselling, and quarterly utilisation reporting.
            </p>
            <div className="grid sm:grid-cols-2 gap-4 pt-2">
              <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                <p className="font-semibold text-white">Employee Assistance (EAP)</p>
                <p className="text-xs text-white/70 mt-1">Confidential 1:1 care & critical incident debriefing.</p>
              </div>
              <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                <p className="font-semibold text-white">Psychosocial Risk Audits</p>
                <p className="text-xs text-white/70 mt-1">ISO 45003 hazard assessments & board reporting.</p>
              </div>
            </div>
            <div className="pt-2">
              <Link
                to="/corporate-wellness"
                data-testid="corporate-consultation-btn"
                className="inline-flex items-center gap-2 px-8 py-4 rounded-full bg-[#D4A373] text-[#1C3F3A] font-bold text-sm hover:bg-white transition-all shadow-lg"
              >
                <span>Request a Consultation</span>
                <ArrowRight size={16} />
              </Link>
            </div>
          </div>

          <div className="lg:col-span-6">
            <div className="bg-white/5 border border-white/10 rounded-3xl p-8 space-y-6">
              <h3 className="text-xl font-semibold text-white">What our corporate partners receive:</h3>
              <ul className="space-y-3.5 text-sm text-white/85">
                <li className="flex items-start gap-3">
                  <span className="w-5 h-5 rounded-full bg-[#D4A373]/20 text-[#D4A373] flex items-center justify-center flex-shrink-0 text-xs font-bold mt-0.5">✓</span>
                  <span><strong>Dedicated EAP Helpline:</strong> Rapid clinical intake for employees and dependants.</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="w-5 h-5 rounded-full bg-[#D4A373]/20 text-[#D4A373] flex items-center justify-center flex-shrink-0 text-xs font-bold mt-0.5">✓</span>
                  <span><strong>Quarterly Trend Reports:</strong> Anonymised, board-level analytics on stress drivers.</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="w-5 h-5 rounded-full bg-[#D4A373]/20 text-[#D4A373] flex items-center justify-center flex-shrink-0 text-xs font-bold mt-0.5">✓</span>
                  <span><strong>Crisis Debriefing:</strong> Immediate response following traumatic workplace incidents.</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 6 — TRAINING & TEAM BUILDING */}
      <section className="section bg-white" data-testid="training-spotlight">
        <div className="container-x">
          <SectionHeading
            eyebrow="Developmental Support"
            title="Experiential team building & high-impact corporate training."
            description="Transform workplace culture, rebuild interpersonal trust, and equip leaders with resilient operating rhythms."
            center
          />

          <div className="mt-12 grid lg:grid-cols-3 gap-8">
            <div className="bg-[#FAFAFA] border border-slate-200 rounded-2xl p-7 space-y-4">
              <div className="w-10 h-10 rounded-lg bg-[#D4A373]/20 text-[#D4A373] flex items-center justify-center font-bold">01</div>
              <h3 className="text-xl font-bold text-[#0F172A]">Experiential Team Building</h3>
              <p className="text-sm text-[#475569] leading-relaxed">
                Full-day and multi-day retreats that move beyond generic games to tackle real communication friction, psychological safety, and team alignment.
              </p>
            </div>

            <div className="bg-[#FAFAFA] border border-slate-200 rounded-2xl p-7 space-y-4">
              <div className="w-10 h-10 rounded-lg bg-[#1C3F3A]/15 text-[#1C3F3A] flex items-center justify-center font-bold">02</div>
              <h3 className="text-xl font-bold text-[#0F172A]">Resilience & Burnout Prevention</h3>
              <p className="text-sm text-[#475569] leading-relaxed">
                Practical, evidence-led workshops for high-pressure teams to identify early exhaustion indicators and build daily micro-recovery habits.
              </p>
            </div>

            <div className="bg-[#FAFAFA] border border-slate-200 rounded-2xl p-7 space-y-4">
              <div className="w-10 h-10 rounded-lg bg-[#81B29A]/20 text-[#1C3F3A] flex items-center justify-center font-bold">03</div>
              <h3 className="text-xl font-bold text-[#0F172A]">Difficult Conversations</h3>
              <p className="text-sm text-[#475569] leading-relaxed">
                Equip line managers and team leads with conversational scripts to address underperformance, conflict, and behavioural issues cleanly.
              </p>
            </div>
          </div>

          <div className="mt-10 text-center">
            <Link to="/training-team-building" className="btn-primary inline-flex items-center gap-2">
              <span>Request a Customised Quote</span>
              <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </section>

      {/* SECTION 7 — FEATURED ONLINE OFFER (KAJABI CONFIGURABLE) */}
      <section className="section bg-[#F1F5F2]" data-testid="featured-offer-section">
        <div className="container-x">
          <div className="bg-white rounded-3xl border border-slate-200/80 p-8 sm:p-12 shadow-sm grid lg:grid-cols-12 gap-8 items-center">
            <div className="lg:col-span-8 space-y-4">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#D4A373]/20 text-xs font-bold text-[#1C3F3A]">
                <Sparkles size={13} />
                <span>{FEATURED_OFFER.badge}</span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold text-[#0F172A]">
                {FEATURED_OFFER.title}
              </h2>
              <p className="text-base text-[#475569] leading-relaxed">
                {FEATURED_OFFER.description}
              </p>
              <div className="pt-2 flex flex-wrap gap-4 items-center">
                <a
                  href={FEATURED_OFFER.kajabi_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-primary flex items-center gap-2"
                >
                  <span>{FEATURED_OFFER.cta_text}</span>
                  <ArrowUpRight size={16} />
                </a>
                <Link to="/learning" className="text-sm font-semibold text-[#1C3F3A] hover:underline">
                  Browse all 6 online courses →
                </Link>
              </div>
            </div>

            <div className="lg:col-span-4 flex justify-center">
              <div className="w-full max-w-xs p-6 bg-[#1C3F3A] text-white rounded-2xl text-center space-y-3 shadow-lg">
                <FileText size={36} className="mx-auto text-[#D4A373]" />
                <p className="font-bold text-lg">Self-Paced Learning</p>
                <p className="text-xs text-white/70">Instant online access via FCA Kajabi Member Hub.</p>
                <span className="inline-block text-[11px] px-3 py-1 rounded-full bg-white/10 text-[#D4A373]">
                  CPD-Friendly Modules
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 8 — HOW IT WORKS (3 STEPS) */}
      <section className="section bg-white" data-testid="how-it-works">
        <div className="container-x">
          <SectionHeading
            eyebrow="Simple 3-Step Flow"
            title="How to begin your support journey with FCA."
            description="Clear, zero-friction steps to connect with the right service."
            center
          />

          <div className="mt-12 grid md:grid-cols-3 gap-8">
            {HOW_IT_WORKS_STEPS.map((s) => (
              <div key={s.step} className="bg-[#FAFAFA] border border-slate-100 rounded-2xl p-8 space-y-3">
                <span className="text-4xl font-extrabold text-[#D4A373]">{s.step}</span>
                <h3 className="text-xl font-bold text-[#0F172A]">{s.title}</h3>
                <p className="text-sm text-[#475569] leading-relaxed">{s.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SECTION 9 & 10 — CLOSING CONVERSION BANNER */}
      <CTABanner
        title="Need help choosing? Talk to FCA."
        subtitle="Our team in Gaborone will guide you to the right counselling, corporate wellness, or training programme."
        ctaLabel="Contact Us Today"
        ctaTo="/contact"
      />
    </>
  );
}

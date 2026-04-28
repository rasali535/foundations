import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowUpRight,
  ShieldCheck,
  HeartPulse,
  GraduationCap,
  LineChart,
  Sparkles,
  ArrowRight,
} from "lucide-react";

import Reveal from "@/components/Reveal";
import Counter from "@/components/Counter";
import SectionHeading from "@/components/SectionHeading";
import CTABanner from "@/components/CTABanner";
import {
  HERO_IMG,
  FRAMEWORK_IMG,
  SERVICES,
  PILLARS,
  METRICS,
  INDUSTRIES,
  COURSES,
  SITE,
} from "@/data/site";

const SERVICE_ICONS = {
  "eap-counselling": HeartPulse,
  "corporate-training": GraduationCap,
  "psychosocial-risk": ShieldCheck,
  "organisational-development": LineChart,
};

export default function Home() {
  return (
    <>
      {/* Hero */}
      <section
        data-testid="home-hero"
        className="relative min-h-[88vh] flex items-end overflow-hidden"
      >
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: `url(${HERO_IMG})` }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/30 via-black/20 to-[#FAFAFA]" />
        <div className="grain" />

        <div className="relative container-x pb-20 md:pb-28 grid md:grid-cols-12 gap-10 items-end">
          <div className="md:col-span-8">
            <motion.p
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.6 }}
              className="eyebrow text-white/90"
            >
              {SITE.parent} · Botswana
            </motion.p>
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.7 }}
              className="mt-5 text-4xl sm:text-5xl lg:text-7xl tracking-tight leading-[1.02] font-semibold text-white max-w-4xl"
            >
              Workplaces where{" "}
              <span className="italic text-[#D4A373]">people thrive</span> —
              measurably.
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35, duration: 0.7 }}
              className="mt-6 text-lg text-white/85 max-w-2xl leading-relaxed"
            >
              We're a workplace mental health and organisational development
              consultancy helping leaders reduce psychosocial risk, lift
              wellbeing, and build cultures that perform.
            </motion.p>
            <motion.div
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.7 }}
              className="mt-10 flex flex-wrap gap-4"
            >
              <Link
                to="/contact"
                data-testid="hero-cta-primary"
                className="btn-primary"
              >
                Book a consultation
                <ArrowUpRight size={18} />
              </Link>
              <Link
                to="/services"
                data-testid="hero-cta-secondary"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-full text-white border border-white/40 hover:bg-white/10 transition"
              >
                Explore services
                <ArrowRight size={16} />
              </Link>
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7, duration: 0.7 }}
            className="md:col-span-4"
          >
            <div className="backdrop-blur-xl bg-white/15 border border-white/30 rounded-2xl p-6 text-white">
              <Sparkles size={20} className="text-[#D4A373]" />
              <p className="mt-3 text-sm text-white/80 leading-relaxed">
                ISO 45003 aligned · trauma-informed · board-ready reporting.
                Designed for regulated, high-stakes industries.
              </p>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Metrics strip */}
      <section className="relative -mt-16 z-10">
        <div className="container-x">
          <Reveal>
            <div className="bg-white border border-slate-100 rounded-2xl shadow-[0_30px_60px_-20px_rgba(0,0,0,0.08)] grid grid-cols-2 md:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-slate-100">
              {METRICS.map((m, i) => (
                <div key={i} className="px-6 py-8 text-center md:text-left">
                  <p className="text-4xl md:text-5xl font-semibold text-[#1C3F3A] tracking-tight">
                    <Counter to={m.value} suffix={m.suffix} />
                  </p>
                  <p className="mt-1 text-xs uppercase tracking-[0.2em] text-[#475569]">
                    {m.label}
                  </p>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      {/* Services preview */}
      <section className="section">
        <div className="container-x">
          <SectionHeading
            eyebrow="What we do"
            title="Four practices, one integrated answer to workplace wellbeing."
            description="From confidential counselling and crisis response to ISO-aligned risk programmes — every engagement plugs into the same measurement spine."
            testid="home-services-heading"
          />

          <div className="mt-14 grid md:grid-cols-2 gap-6">
            {SERVICES.map((s, i) => {
              const Icon = SERVICE_ICONS[s.slug];
              return (
                <Reveal key={s.slug} delay={i * 0.05}>
                  <Link
                    to={`/services/${s.slug}`}
                    data-testid={`home-service-${s.slug}`}
                    className="group block bg-white border border-slate-100 rounded-2xl p-8 hover:-translate-y-1 hover:shadow-[0_20px_40px_-15px_rgba(28,63,58,0.18)] transition-all duration-300"
                  >
                    <div className="flex items-start justify-between mb-6">
                      <div className="w-12 h-12 rounded-xl bg-[#F1F5F2] flex items-center justify-center text-[#1C3F3A]">
                        <Icon size={22} />
                      </div>
                      <span className="text-[10px] uppercase tracking-[0.2em] text-[#81B29A] mt-2">
                        {s.category}
                      </span>
                    </div>
                    <h3 className="text-2xl font-medium text-[#0F172A] tracking-tight">
                      {s.title}
                    </h3>
                    <p className="mt-3 text-[#475569] leading-relaxed">
                      {s.short}
                    </p>
                    <span className="mt-6 inline-flex items-center gap-2 text-sm text-[#1C3F3A] font-medium group-hover:gap-3 transition-all">
                      Learn more <ArrowRight size={16} />
                    </span>
                  </Link>
                </Reveal>
              );
            })}
          </div>
        </div>
      </section>

      {/* Four pillars preview */}
      <section className="section bg-[#F1F5F2] relative overflow-hidden">
        <div
          className="absolute inset-0 opacity-20 bg-cover bg-center"
          style={{ backgroundImage: `url(${FRAMEWORK_IMG})` }}
        />
        <div className="relative container-x">
          <SectionHeading
            eyebrow="Our approach"
            title="The Four Pillars Framework"
            description="A repeatable, evidence-led method that turns intent into outcomes — and outcomes into reportable change."
            testid="home-approach-heading"
          />

          <div className="mt-14 grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {PILLARS.map((p, i) => (
              <Reveal key={p.n} delay={i * 0.08}>
                <div
                  data-testid={`pillar-${p.n}`}
                  className="bg-white border border-white rounded-2xl p-7 h-full hover:-translate-y-1 transition-transform"
                >
                  <p className="text-sm font-medium text-[#D4A373]">{p.n}</p>
                  <h3 className="mt-3 text-xl font-medium text-[#0F172A]">
                    {p.title}
                  </h3>
                  <p className="mt-3 text-[#475569] text-sm leading-relaxed">
                    {p.body}
                  </p>
                </div>
              </Reveal>
            ))}
          </div>

          <div className="mt-12 flex justify-center">
            <Link
              to="/approach"
              data-testid="home-approach-cta"
              className="btn-ghost"
            >
              Read the full framework
              <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </section>

      {/* Industries strip */}
      <section className="section">
        <div className="container-x">
          <SectionHeading
            eyebrow="Industries"
            title="Trusted across regulated, high-stakes sectors."
          />
          <div className="mt-12 grid grid-cols-2 md:grid-cols-5 gap-4">
            {INDUSTRIES.map((ind, i) => (
              <Reveal key={ind.slug} delay={i * 0.05}>
                <div className="border border-slate-200 rounded-xl px-5 py-6 text-center hover:bg-[#1C3F3A] hover:text-white transition-colors">
                  <p className="font-medium tracking-tight">{ind.title}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>
              
      {/* Personal development preview */}
      <section className="section bg-[#F1F5F2]">
        <div className="container-x">
          <div className="grid md:grid-cols-12 gap-10 items-end mb-12">
            <div className="md:col-span-7">
              <SectionHeading
                eyebrow="Learning · Personal development"
                title="Online courses to grow the work-self."
                description="Self-paced, evidence-led courses delivered through our learning platform. CPD-friendly, designed for working professionals."
              />
            </div>
            <div className="md:col-span-5 md:text-right">
              <Link
                to="/learning"
                data-testid="home-learning-cta"
                className="btn-primary"
              >
                Browse all courses
                <ArrowRight size={16} />
              </Link>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {COURSES.slice(0, 3).map((c, i) => (
              <Reveal key={c.slug} delay={i * 0.05}>
                <Link
                  to="/learning"
                  data-testid={`home-course-${c.slug}`}
                  className="group block bg-white rounded-2xl overflow-hidden h-full hover:-translate-y-1 hover:shadow-[0_18px_36px_-15px_rgba(28,63,58,0.18)] transition-all"
                >
                  <div
                    className="h-32 relative"
                    style={{
                      background: `linear-gradient(135deg, ${c.accent}, #1C3F3A)`,
                    }}
                  >
                    <div className="absolute inset-0 grain opacity-20" />
                    <span className="absolute top-4 left-4 text-[10px] uppercase tracking-[0.2em] bg-black/20 backdrop-blur-sm text-white/90 px-3 py-1 rounded-full">
                      {c.category}
                    </span>
                    <GraduationCap
                      className="absolute bottom-4 left-4 text-white/80"
                      size={24}
                    />
                  </div>
                  <div className="p-6">
                    <h3 className="text-lg font-medium text-[#0F172A] tracking-tight">
                      {c.title}
                    </h3>
                    <p className="mt-2 text-sm text-[#475569]">
                      {c.duration} · {c.cpd}
                    </p>
                    <span className="mt-5 inline-flex items-center gap-2 text-sm text-[#1C3F3A] font-medium group-hover:gap-3 transition-all">
                      View course <ArrowRight size={14} />
                    </span>
                  </div>
                </Link>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <CTABanner />
      <div className="h-24" />
    </>
  );
}

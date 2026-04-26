import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  Clock,
  Layers,
  GraduationCap,
  Award,
  Check,
} from "lucide-react";

import Reveal from "@/components/Reveal";
import SectionHeading from "@/components/SectionHeading";
import CTABanner from "@/components/CTABanner";
import { COURSES, COURSE_CATEGORIES, MOODLE_URL, MOODLE_LOGIN_HINT } from "@/data/site";

export default function Learning() {
  const [filter, setFilter] = useState("All");

  const filtered = useMemo(() => {
    if (filter === "All") return COURSES;
    return COURSES.filter((c) => c.category === filter);
  }, [filter]);

  return (
    <>
      <section className="section pt-16">
        <div className="container-x">
          <SectionHeading
            eyebrow="Learning · Personal development"
            title="Online courses for the work-self that wants to keep growing."
            description="Self-paced, evidence-led, and CPD-friendly. Enrol on our learning platform — start, pause and return whenever life lets you. New courses added each quarter."
            testid="learning-heading"
          />
          <Reveal delay={0.1}>
            <div className="mt-10 flex flex-wrap items-center gap-3">
              <a
                href={MOODLE_URL}
                target="_blank"
                rel="noopener noreferrer"
                data-testid="learning-platform-cta"
                className="btn-primary"
              >
                Open the learning platform
                <ArrowUpRight size={16} />
              </a>
              <a
                href="/contact"
                className="btn-ghost"
                data-testid="learning-corporate-cta"
              >
                Enrol your team
              </a>
            </div>
            <p className="mt-4 text-xs text-[#475569]" data-testid="moodle-hint">
              <span className="inline-block w-2 h-2 rounded-full bg-[#D4A373] mr-2 align-middle" />
              {MOODLE_LOGIN_HINT}
            </p>
          </Reveal>
        </div>
      </section>

      {/* Filter chips */}
      <section className="container-x">
        <Reveal>
          <div className="flex flex-wrap items-center gap-2 mb-10">
            {COURSE_CATEGORIES.map((c) => (
              <button
                key={c}
                onClick={() => setFilter(c)}
                data-testid={`learning-filter-${c.toLowerCase().replace(/\s+/g, "-")}`}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                  filter === c
                    ? "bg-[#1C3F3A] text-white"
                    : "bg-white text-[#475569] border border-slate-200 hover:border-[#1C3F3A] hover:text-[#1C3F3A]"
                }`}
              >
                {c}
              </button>
            ))}
          </div>
        </Reveal>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map((c, i) => {
            const moodleUrl = `${MOODLE_URL}${c.moodlePath}`;
            return (
              <Reveal key={c.slug} delay={i * 0.05}>
                <article
                  data-testid={`course-card-${c.slug}`}
                  className="group bg-white border border-slate-100 rounded-2xl overflow-hidden h-full flex flex-col hover:-translate-y-1 hover:shadow-[0_18px_36px_-15px_rgba(28,63,58,0.18)] transition-all"
                >
                  <Link to={`/learning/${c.slug}`} className="block">
                    <div
                      className="h-40 relative overflow-hidden"
                      style={{
                        background: `linear-gradient(135deg, ${c.accent}, #1C3F3A)`,
                      }}
                    >
                      <div className="absolute inset-0 grain opacity-20" />
                      <div className="absolute top-5 left-5 right-5 flex items-center justify-between text-white/90">
                        <span className="text-[10px] uppercase tracking-[0.2em] bg-black/20 backdrop-blur-sm px-3 py-1 rounded-full">
                          {c.category}
                        </span>
                        <span className="text-[10px] uppercase tracking-[0.2em]">
                          {c.level}
                        </span>
                      </div>
                      <div className="absolute bottom-5 left-5 right-5 text-white">
                        <GraduationCap size={28} className="opacity-80" />
                      </div>
                    </div>
                  </Link>

                  <div className="p-7 flex-1 flex flex-col">
                    <Link to={`/learning/${c.slug}`}>
                      <h3 className="text-xl font-semibold text-[#0F172A] tracking-tight hover:text-[#1C3F3A] transition-colors">
                        {c.title}
                      </h3>
                    </Link>
                    <p className="mt-3 text-sm text-[#475569] leading-relaxed">
                      {c.summary}
                    </p>

                    <ul className="mt-5 space-y-2 text-sm text-[#0F172A]">
                      {c.outcomes.slice(0, 2).map((o) => (
                        <li key={o} className="flex gap-2 items-start">
                          <span className="mt-1 w-4 h-4 rounded-full bg-[#F1F5F2] text-[#1C3F3A] flex items-center justify-center flex-shrink-0">
                            <Check size={10} />
                          </span>
                          <span>{o}</span>
                        </li>
                      ))}
                    </ul>

                    <div className="mt-6 pt-5 border-t border-slate-100 grid grid-cols-3 gap-2 text-xs text-[#475569]">
                      <Meta icon={Clock} label={c.duration.split(" · ")[0]} />
                      <Meta icon={Layers} label={`${c.modules} modules`} />
                      <Meta icon={Award} label={c.cpd} />
                    </div>

                    <div className="mt-7 flex items-center gap-2">
                      <Link
                        to={`/learning/${c.slug}`}
                        data-testid={`course-preview-${c.slug}`}
                        className="flex-1 inline-flex items-center justify-center gap-2 px-5 py-3 rounded-full bg-[#1C3F3A] text-white text-sm font-medium hover:bg-[#15302C] transition-colors"
                      >
                        Preview course
                      </Link>
                      <a
                        href={moodleUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        data-testid={`course-cta-${c.slug}`}
                        aria-label="Open on Moodle"
                        className="w-11 h-11 inline-flex items-center justify-center rounded-full border border-[#1C3F3A] text-[#1C3F3A] hover:bg-[#1C3F3A] hover:text-white transition-colors"
                      >
                        <ArrowUpRight size={16} />
                      </a>
                    </div>
                  </div>
                </article>
              </Reveal>
            );
          })}
        </div>
      </section>

      <div className="h-24" />

      {/* How it works */}
      <section className="section bg-[#F1F5F2]">
        <div className="container-x">
          <SectionHeading
            eyebrow="How learning works"
            title="Self-paced, supported, and built around real workdays."
          />
          <div className="mt-12 grid md:grid-cols-3 gap-6">
            {STEPS.map((s, i) => (
              <Reveal key={s.t} delay={i * 0.05}>
                <div className="bg-white rounded-2xl p-7 h-full border border-white">
                  <p className="text-5xl font-semibold text-[#D4A373] tracking-tight">
                    0{i + 1}
                  </p>
                  <h3 className="mt-4 text-xl font-medium text-[#0F172A]">
                    {s.t}
                  </h3>
                  <p className="mt-3 text-sm text-[#475569] leading-relaxed">
                    {s.b}
                  </p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <CTABanner
        title="Want to roll out learning across your team?"
        subtitle="We licence cohorts, run kick-off webinars and report progress to HR. Let's talk volumes."
        ctaLabel="Talk to us"
      />
      <div className="h-24" />
    </>
  );
}

function Meta({ icon: Icon, label }) {
  return (
    <div className="flex items-center gap-1.5">
      <Icon size={13} className="text-[#81B29A]" />
      <span>{label}</span>
    </div>
  );
}

const STEPS = [
  {
    t: "Enrol on the platform",
    b: "Sign in (or create an account) to our Moodle-based learning portal. One login, all your courses.",
  },
  {
    t: "Learn at your pace",
    b: "Short video lessons, reflective prompts, downloadable workbooks and quick checks for understanding.",
  },
  {
    t: "Earn your CPD certificate",
    b: "Complete the final assessment to download a CPD-verifiable certificate to add to your profile.",
  },
];

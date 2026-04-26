import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowUpRight,
  Play,
  CheckCircle2,
  Circle,
  Clock,
  Layers,
  Award,
  FileText,
  Download,
  Lock,
  GraduationCap,
} from "lucide-react";

import Reveal from "@/components/Reveal";
import { COURSES, MOODLE_URL, MOODLE_LOGIN_HINT } from "@/data/site";

const TABS = ["Overview", "Modules", "Resources", "Assessment"];

export default function CoursePreview() {
  const { slug } = useParams();
  const course = COURSES.find((c) => c.slug === slug);
  const [tab, setTab] = useState("Overview");
  const [completed, setCompleted] = useState([0]); // first module done

  if (!course) {
    return (
      <section className="section container-x">
        <p className="text-[#475569]">Course not found.</p>
        <Link to="/learning" className="btn-ghost mt-6 inline-flex">
          <ArrowLeft size={16} /> Back to learning
        </Link>
      </section>
    );
  }

  const moodleUrl = `${MOODLE_URL}${course.moodlePath}`;
  const modules = generateModules(course);
  const progress = Math.round((completed.length / modules.length) * 100);

  const toggle = (i) => {
    setCompleted((prev) =>
      prev.includes(i) ? prev.filter((x) => x !== i) : [...prev, i]
    );
  };

  return (
    <>
      {/* Hero strip */}
      <section
        className="relative overflow-hidden"
        style={{
          background: `linear-gradient(135deg, ${course.accent}, #1C3F3A)`,
        }}
      >
        <div className="grain" />
        <div className="relative container-x py-16 md:py-20 text-white">
          <Link
            to="/learning"
            data-testid="course-back"
            className="inline-flex items-center gap-2 text-white/80 hover:text-white text-sm mb-8"
          >
            <ArrowLeft size={16} /> Back to learning
          </Link>

          <div className="grid md:grid-cols-12 gap-10 items-end">
            <div className="md:col-span-8">
              <div className="flex flex-wrap items-center gap-3 text-xs uppercase tracking-[0.2em] text-white/80">
                <span className="bg-white/15 backdrop-blur-sm px-3 py-1 rounded-full">
                  {course.category}
                </span>
                <span>{course.level}</span>
                <span>·</span>
                <span>{course.cpd}</span>
              </div>
              <h1 className="mt-5 text-4xl sm:text-5xl lg:text-6xl font-semibold tracking-tight leading-[1.05]">
                {course.title}
              </h1>
              <p className="mt-5 text-lg text-white/85 max-w-2xl leading-relaxed">
                {course.summary}
              </p>
            </div>

            <div className="md:col-span-4">
              <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl p-6">
                <p className="text-xs uppercase tracking-[0.2em] text-white/70">
                  Your progress
                </p>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className="text-4xl font-semibold">{progress}%</span>
                  <span className="text-sm text-white/70">
                    · {completed.length}/{modules.length} modules
                  </span>
                </div>
                <div className="mt-4 h-2 bg-white/15 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#D4A373] transition-all duration-500"
                    style={{ width: `${progress}%` }}
                    data-testid="course-progress-bar"
                  />
                </div>
                <a
                  href={moodleUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid="course-open-moodle"
                  className="mt-6 w-full inline-flex items-center justify-between gap-2 px-5 py-3 rounded-full bg-[#D4A373] text-[#1C3F3A] text-sm font-medium hover:bg-white transition-colors"
                >
                  Continue on Moodle
                  <ArrowUpRight size={16} />
                </a>
                <p className="mt-3 text-[11px] text-white/60 leading-relaxed">
                  This is an in-site preview. Full lessons, quizzes and
                  certificate live on our learning platform.
                </p>
                <p className="mt-2 text-[11px] text-[#D4A373]">
                  {MOODLE_LOGIN_HINT}
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Tabs */}
      <section className="border-b border-slate-100 sticky top-20 bg-[#FAFAFA]/85 backdrop-blur-md z-30">
        <div className="container-x flex gap-2 overflow-x-auto">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              data-testid={`course-tab-${t.toLowerCase()}`}
              className={`px-5 py-4 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                tab === t
                  ? "border-[#1C3F3A] text-[#1C3F3A]"
                  : "border-transparent text-[#475569] hover:text-[#1C3F3A]"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </section>

      {/* Body */}
      <section className="section pt-12">
        <div className="container-x grid md:grid-cols-12 gap-10">
          <div className="md:col-span-8 space-y-10">
            {tab === "Overview" && (
              <Reveal>
                <h2 className="text-2xl font-semibold text-[#0F172A]">
                  About this course
                </h2>
                <p className="mt-4 text-[#475569] leading-relaxed">
                  {course.summary} Designed for working professionals across
                  Southern Africa, this course distils contemporary
                  evidence-based practice into short, actionable modules you
                  can complete around your workday.
                </p>

                <h3 className="mt-10 text-xl font-semibold text-[#0F172A]">
                  What you'll be able to do
                </h3>
                <ul className="mt-5 space-y-3">
                  {course.outcomes.map((o) => (
                    <li
                      key={o}
                      className="flex items-start gap-3 text-[#0F172A]"
                    >
                      <CheckCircle2
                        size={20}
                        className="text-[#81B29A] mt-0.5 flex-shrink-0"
                      />
                      <span>{o}</span>
                    </li>
                  ))}
                </ul>

                <h3 className="mt-10 text-xl font-semibold text-[#0F172A]">
                  Who it's for
                </h3>
                <p className="mt-3 text-[#475569] leading-relaxed">
                  Line managers, HR business partners, team leads and any
                  professional who wants a practical, evidence-led toolkit —
                  no clinical background required.
                </p>
              </Reveal>
            )}

            {tab === "Modules" && (
              <Reveal>
                <h2 className="text-2xl font-semibold text-[#0F172A]">
                  Course modules
                </h2>
                <p className="mt-3 text-sm text-[#475569]">
                  Tick off as you go. Full video and assessment open on Moodle.
                </p>
                <ul className="mt-8 space-y-3">
                  {modules.map((m, i) => {
                    const done = completed.includes(i);
                    const locked = i > completed.length;
                    return (
                      <li
                        key={i}
                        data-testid={`course-module-${i}`}
                        className={`bg-white border rounded-2xl p-5 flex items-start gap-4 transition-all ${
                          done
                            ? "border-[#81B29A]/40 bg-[#F1F5F2]/60"
                            : "border-slate-100"
                        }`}
                      >
                        <button
                          onClick={() => !locked && toggle(i)}
                          disabled={locked}
                          aria-label="toggle module"
                          className={`mt-1 ${locked ? "cursor-not-allowed" : ""}`}
                        >
                          {locked ? (
                            <Lock size={20} className="text-slate-300" />
                          ) : done ? (
                            <CheckCircle2
                              size={20}
                              className="text-[#1C3F3A]"
                            />
                          ) : (
                            <Circle
                              size={20}
                              className="text-slate-300 hover:text-[#1C3F3A]"
                            />
                          )}
                        </button>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-3">
                            <p
                              className={`font-medium ${
                                done ? "text-[#1C3F3A]" : "text-[#0F172A]"
                              }`}
                            >
                              {`Module ${String(i + 1).padStart(2, "0")} · ${m.title}`}
                            </p>
                            <span className="flex items-center gap-1.5 text-xs text-[#475569] flex-shrink-0">
                              <Clock size={13} /> {m.minutes} min
                            </span>
                          </div>
                          <p className="mt-1 text-sm text-[#475569] leading-relaxed">
                            {m.summary}
                          </p>
                          <div className="mt-3 flex items-center gap-3 text-xs text-[#81B29A]">
                            <span className="flex items-center gap-1.5">
                              <Play size={12} /> Video
                            </span>
                            <span>·</span>
                            <span>Reflection</span>
                            <span>·</span>
                            <span>Quick check</span>
                          </div>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </Reveal>
            )}

            {tab === "Resources" && (
              <Reveal>
                <h2 className="text-2xl font-semibold text-[#0F172A]">
                  Downloadable resources
                </h2>
                <p className="mt-3 text-sm text-[#475569]">
                  Workbooks and reference cards. Full library available on
                  Moodle.
                </p>
                <ul className="mt-8 space-y-3">
                  {RESOURCES(course).map((r) => (
                    <li
                      key={r.name}
                      className="flex items-center gap-4 bg-white border border-slate-100 rounded-2xl p-5 hover:border-[#1C3F3A]/30 transition-colors"
                    >
                      <div className="w-10 h-10 rounded-lg bg-[#F1F5F2] flex items-center justify-center text-[#1C3F3A]">
                        <FileText size={18} />
                      </div>
                      <div className="flex-1">
                        <p className="font-medium text-[#0F172A]">{r.name}</p>
                        <p className="text-xs text-[#475569]">
                          {r.type} · {r.size}
                        </p>
                      </div>
                      <a
                        href={moodleUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="w-10 h-10 rounded-full bg-[#1C3F3A] text-white flex items-center justify-center hover:bg-[#15302C]"
                        aria-label={`Download ${r.name}`}
                      >
                        <Download size={16} />
                      </a>
                    </li>
                  ))}
                </ul>
              </Reveal>
            )}

            {tab === "Assessment" && (
              <Reveal>
                <h2 className="text-2xl font-semibold text-[#0F172A]">
                  Assessment & certification
                </h2>
                <div className="mt-6 bg-white border border-slate-100 rounded-2xl p-7">
                  <Award size={28} className="text-[#D4A373]" />
                  <h3 className="mt-4 text-xl font-medium text-[#0F172A]">
                    Final assessment ({course.cpd})
                  </h3>
                  <p className="mt-3 text-[#475569] leading-relaxed">
                    Complete all modules, then take a 20-question scenario-based
                    quiz. Pass at 80%+ and instantly download a CPD-verifiable
                    certificate to your inbox and Moodle profile.
                  </p>
                  <a
                    href={moodleUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-primary mt-6"
                  >
                    Start assessment on Moodle
                    <ArrowUpRight size={16} />
                  </a>
                </div>
              </Reveal>
            )}
          </div>

          {/* Sidebar */}
          <aside className="md:col-span-4 space-y-4">
            <Reveal>
              <div className="bg-white border border-slate-100 rounded-2xl p-6">
                <p className="eyebrow">Course details</p>
                <ul className="mt-5 space-y-4 text-sm">
                  <SideRow icon={Clock} k="Duration" v={course.duration} />
                  <SideRow
                    icon={Layers}
                    k="Modules"
                    v={`${course.modules} self-paced`}
                  />
                  <SideRow
                    icon={GraduationCap}
                    k="Level"
                    v={course.level}
                  />
                  <SideRow icon={Award} k="CPD" v={course.cpd} />
                </ul>
              </div>
            </Reveal>

            <Reveal delay={0.05}>
              <div className="bg-[#F1F5F2] border border-[#E2E8F0] rounded-2xl p-6">
                <p className="eyebrow">Need a team licence?</p>
                <p className="mt-3 text-sm text-[#475569] leading-relaxed">
                  We licence cohorts of 10+ with kick-off webinars and HR
                  progress reporting.
                </p>
                <Link
                  to="/contact"
                  data-testid="course-team-licence-cta"
                  className="btn-ghost mt-5 w-full justify-center text-sm"
                >
                  Talk to us
                </Link>
              </div>
            </Reveal>
          </aside>
        </div>
      </section>
    </>
  );
}

function SideRow({ icon: Icon, k, v }) {
  return (
    <li className="flex items-start gap-3">
      <Icon size={16} className="text-[#81B29A] mt-0.5" />
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-[#475569]">{k}</p>
        <p className="text-[#0F172A] font-medium">{v}</p>
      </div>
    </li>
  );
}

function generateModules(course) {
  // Build a coherent module list from course outcomes + generic scaffold
  const titles = [
    "Foundations & framing",
    "The science behind it",
    course.outcomes[0] || "Core practice",
    course.outcomes[1] || "Apply at work",
    course.outcomes[2] || "Embed & sustain",
    "Case studies",
    "Tools & templates",
    "Capstone & assessment",
  ].slice(0, course.modules);

  const summaries = [
    "Set the context, the language and the lens we'll use throughout.",
    "A short, accessible look at the evidence that anchors this work.",
    "Translate the concept into a small, repeatable practice you'll try this week.",
    "Apply the practice to a real situation in your role.",
    "Build the rituals that keep this alive after the course ends.",
    "Walk through realistic scenarios and how peers approached them.",
    "Worksheets and scripts you can adapt and reuse.",
    "Reflect, integrate and complete the certifying assessment.",
  ];

  return titles.map((t, i) => ({
    title: t,
    summary: summaries[i],
    minutes: 18 + (i * 4) % 20,
  }));
}

function RESOURCES(course) {
  return [
    { name: `${course.title} — Workbook`, type: "PDF", size: "1.8 MB" },
    { name: "Reflection prompts", type: "PDF", size: "320 KB" },
    { name: "Manager conversation script", type: "PDF", size: "210 KB" },
    { name: "Reading list & references", type: "PDF", size: "180 KB" },
  ];
}

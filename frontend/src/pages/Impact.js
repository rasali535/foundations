import Reveal from "@/components/Reveal";
import Counter from "@/components/Counter";
import SectionHeading from "@/components/SectionHeading";
import CTABanner from "@/components/CTABanner";
import { METRICS, IMPACT_IMG } from "@/data/site";

const CATEGORIES = [
  {
    tag: "Preventative",
    items: [
      "ISO 45003 psychosocial-risk baselines",
      "Wellbeing strategy & policy design",
      "Manager mental health literacy",
    ],
  },
  {
    tag: "Responsive",
    items: [
      "Confidential employee counselling",
      "Critical-incident & trauma response",
      "Crisis & 24/7 helpline access",
    ],
  },
  {
    tag: "Developmental",
    items: [
      "Leadership & resilience programmes",
      "Culture & change consulting",
      "Team effectiveness coaching",
    ],
  },
];

export default function Impact() {
  return (
    <>
      <section className="relative section pt-16 overflow-hidden">
        <div
          className="absolute right-0 top-0 w-1/2 h-full opacity-30 bg-cover bg-center hidden md:block"
          style={{ backgroundImage: `url(${IMPACT_IMG})` }}
        />
        <div className="relative container-x">
          <SectionHeading
            eyebrow="Impact · Capability statement"
            title="Outcomes you can take to the board."
            description="We exist to make wellbeing reportable. Here's what the work looks like in numbers, in scope and in the categories of capability we deliver."
            testid="impact-heading"
          />
        </div>
      </section>

      <section className="container-x">
        <Reveal>
          <div className="bg-[#1C3F3A] text-white rounded-3xl p-10 md:p-16 grid grid-cols-2 md:grid-cols-4 gap-8 relative overflow-hidden">
            <div className="grain" />
            {METRICS.map((m, i) => (
              <div key={i} className="relative">
                <p className="text-5xl md:text-6xl font-semibold tracking-tight text-[#D4A373]">
                  <Counter to={m.value} suffix={m.suffix} />
                </p>
                <p className="mt-2 text-sm text-white/70 uppercase tracking-[0.2em]">
                  {m.label}
                </p>
              </div>
            ))}
          </div>
        </Reveal>
      </section>

      <section className="section">
        <div className="container-x">
          <SectionHeading
            eyebrow="Capability map"
            title="Three categories. One coherent story."
          />

          <div className="mt-14 grid md:grid-cols-3 gap-6">
            {CATEGORIES.map((c, i) => (
              <Reveal key={c.tag} delay={i * 0.05}>
                <div
                  data-testid={`impact-cat-${c.tag.toLowerCase()}`}
                  className="bg-white border border-slate-100 rounded-2xl p-8 h-full"
                >
                  <span className="text-[10px] uppercase tracking-[0.2em] text-[#D4A373]">
                    {c.tag}
                  </span>
                  <ul className="mt-6 space-y-4">
                    {c.items.map((it) => (
                      <li
                        key={it}
                        className="flex gap-3 items-start text-[#0F172A]"
                      >
                        <span className="mt-2 w-1.5 h-1.5 rounded-full bg-[#1C3F3A] flex-shrink-0" />
                        <span className="leading-relaxed">{it}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="section bg-[#F1F5F2]">
        <div className="container-x grid md:grid-cols-12 gap-10 items-center">
          <div className="md:col-span-6">
            <SectionHeading
              eyebrow="Why us"
              title="Clinical credibility. Consulting clarity."
              description="We are clinicians, organisational psychologists and change practitioners working as one team. That dual fluency is what turns wellbeing programmes into business outcomes."
            />
          </div>
          <div className="md:col-span-6 space-y-4">
            {[
              ["Clinically led", "Senior clinicians supervise every engagement."],
              ["Consulting fluent", "We translate clinical insight into business KPIs."],
              ["Africa-grounded", "Designed for our regulatory and cultural context."],
              ["Outcome-tied", "Every engagement carries measurable success criteria."],
            ].map(([k, v]) => (
              <Reveal key={k}>
                <div className="bg-white rounded-xl p-6 border border-white">
                  <p className="font-medium text-[#0F172A]">{k}</p>
                  <p className="mt-1 text-sm text-[#475569]">{v}</p>
                </div>
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

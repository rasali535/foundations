import { motion } from "framer-motion";
import Reveal from "@/components/Reveal";
import SectionHeading from "@/components/SectionHeading";
import CTABanner from "@/components/CTABanner";
import { PILLARS, FRAMEWORK_IMG } from "@/data/site";

export default function Approach() {
  return (
    <>
      <section className="relative section pt-16 overflow-hidden">
        <div
          className="absolute inset-0 opacity-15 bg-cover bg-center"
          style={{ backgroundImage: `url(${FRAMEWORK_IMG})` }}
        />
        <div className="relative container-x">
          <SectionHeading
            eyebrow="Our approach"
            title="The Four Pillars Framework — how change actually sticks."
            description="Most wellbeing programmes fail not because the intent is wrong but because the operating model is missing. The Four Pillars give you that operating model."
            testid="approach-heading"
          />
        </div>
      </section>

      <section className="container-x">
        <div className="relative">
          <div className="hidden md:block absolute left-1/2 top-12 bottom-12 w-px bg-gradient-to-b from-transparent via-[#1C3F3A]/30 to-transparent" />
          <div className="space-y-12 md:space-y-24">
            {PILLARS.map((p, i) => (
              <Reveal key={p.n} delay={i * 0.05}>
                <div
                  data-testid={`approach-pillar-${p.n}`}
                  className={`grid md:grid-cols-12 gap-8 items-center ${
                    i % 2 === 1 ? "md:[&>div:first-child]:order-2" : ""
                  }`}
                >
                  <div className="md:col-span-6">
                    <motion.div
                      whileHover={{ y: -4 }}
                      className="bg-white border border-slate-100 rounded-2xl p-10"
                    >
                      <p className="text-6xl font-semibold text-[#D4A373] tracking-tight">
                        {p.n}
                      </p>
                      <h3 className="mt-4 text-3xl font-semibold text-[#0F172A]">
                        {p.title}
                      </h3>
                      <p className="mt-5 text-[#475569] leading-relaxed">
                        {p.body}
                      </p>
                    </motion.div>
                  </div>
                  <div className="md:col-span-6 space-y-4">
                    {APPROACH_DETAILS[i].map((d) => (
                      <div
                        key={d.k}
                        className="flex gap-4 items-start bg-[#F1F5F2] rounded-xl p-5"
                      >
                        <span className="text-[#81B29A] text-xs uppercase tracking-[0.2em] font-medium w-24 mt-1 flex-shrink-0">
                          {d.k}
                        </span>
                        <p className="text-[#0F172A] text-sm leading-relaxed">
                          {d.v}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <div className="h-24" />
      <CTABanner
        title="Want to see the framework applied to your business?"
        subtitle="We'll walk you through a sample diagnostic and the kind of dashboard you'd own."
      />
      <div className="h-24" />
    </>
  );
}

const APPROACH_DETAILS = [
  [
    { k: "Methods", v: "Validated wellbeing & psychosocial-risk surveys, leader interviews, ISO 45003 mapping." },
    { k: "Output", v: "A baseline score, a hot-spot map, and an executive summary you can act on next quarter." },
  ],
  [
    { k: "Methods", v: "Targeted programmes — EAP, training, coaching, culture redesign — chosen for measured fit." },
    { k: "Output", v: "An intervention roadmap with owners, timelines and the exact KPI each move is meant to shift." },
  ],
  [
    { k: "Methods", v: "Manager toolkits, peer-support networks, ritual design, ongoing supervision and coaching." },
    { k: "Output", v: "Behaviour change that survives the post-launch dip — embedded in how managers actually run weeks." },
  ],
  [
    { k: "Methods", v: "Quarterly dashboards covering utilisation, risk, ROI and compliance posture." },
    { k: "Output", v: "Board-ready evidence that lets HR and risk speak the same language as Finance and Audit." },
  ],
];

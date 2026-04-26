import Reveal from "@/components/Reveal";
import SectionHeading from "@/components/SectionHeading";
import CTABanner from "@/components/CTABanner";
import { Heart, Compass, ShieldCheck, Eye } from "lucide-react";
import { SITE } from "@/data/site";

const VALUES = [
  {
    icon: Heart,
    title: "Care, ethically.",
    body:
      "We hold professional, confidential and trauma-informed standards in every engagement.",
  },
  {
    icon: Compass,
    title: "Evidence over opinion.",
    body:
      "We build on validated frameworks — ISO 45003, WHO guidelines and peer-reviewed practice.",
  },
  {
    icon: ShieldCheck,
    title: "Safety as standard.",
    body:
      "Psychological safety isn't a poster — it's a measurable operating discipline.",
  },
  {
    icon: Eye,
    title: "Reportable impact.",
    body:
      "If we can't measure it, we redesign it. Boards deserve numbers, not narratives.",
  },
];

export default function About() {
  return (
    <>
      <section className="section pt-16">
        <div className="container-x grid md:grid-cols-12 gap-10">
          <div className="md:col-span-8">
            <Reveal>
              <p className="eyebrow">About us</p>
            </Reveal>
            <Reveal delay={0.05}>
              <h1 className="mt-4 text-4xl sm:text-5xl lg:text-6xl font-semibold tracking-tight leading-[1.05] text-[#0F172A]">
                We exist so that work doesn't cost people their wellbeing.
              </h1>
            </Reveal>
            <Reveal delay={0.1}>
              <p className="mt-6 text-lg text-[#475569] leading-relaxed max-w-2xl">
                Foundations Counselling Academy was established under the
                Pameltex Group to bring world-class workplace mental health,
                psychosocial risk and organisational development capability to
                organisations operating across Botswana and the broader SADC
                region.
              </p>
            </Reveal>
          </div>
          <div className="md:col-span-4">
            <Reveal delay={0.15}>
              <div className="bg-[#F1F5F2] rounded-2xl p-6 border border-[#E2E8F0]">
                <p className="eyebrow">Headquarters</p>
                <p className="mt-3 text-[#0F172A] font-medium">
                  {SITE.address}
                </p>
                <p className="mt-2 text-sm text-[#475569]">{SITE.hours}</p>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      <section className="section pt-0">
        <div className="container-x grid md:grid-cols-12 gap-12 items-start">
          <div className="md:col-span-5">
            <SectionHeading
              eyebrow="Our mission"
              title="Make psychological safety as obvious as physical safety."
              description="We translate clinical insight, behavioural science and operational pragmatism into systems organisations actually run."
            />
          </div>
          <div className="md:col-span-7 grid md:grid-cols-2 gap-5">
            {VALUES.map((v, i) => (
              <Reveal key={v.title} delay={i * 0.05}>
                <div className="bg-white border border-slate-100 rounded-2xl p-7 h-full">
                  <div className="w-11 h-11 rounded-lg bg-[#F1F5F2] flex items-center justify-center text-[#1C3F3A]">
                    <v.icon size={20} />
                  </div>
                  <h3 className="mt-5 text-xl font-medium text-[#0F172A]">
                    {v.title}
                  </h3>
                  <p className="mt-2 text-[#475569] text-sm leading-relaxed">
                    {v.body}
                  </p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="section bg-[#F1F5F2]">
        <div className="container-x grid md:grid-cols-12 gap-12 items-center">
          <div className="md:col-span-6">
            <SectionHeading
              eyebrow="Strategic positioning"
              title="A Pameltex Group capability — built for board-level conversations."
              description="Foundations Counselling Academy partners with HR, risk, audit and executive leadership. Our methods are designed to translate cleanly into organisational risk registers, ESG narratives and people-strategy KPIs."
            />
          </div>
          <div className="md:col-span-6 grid grid-cols-2 gap-4">
            {[
              ["Confidentiality", "POPIA / GDPR aligned"],
              ["Standards", "ISO 45003 & WHO"],
              ["Reach", "Botswana & SADC"],
              ["Reporting", "Board-grade dashboards"],
            ].map(([k, v]) => (
              <Reveal key={k}>
                <div className="bg-white rounded-xl p-5 border border-white">
                  <p className="text-xs uppercase tracking-[0.2em] text-[#81B29A]">
                    {k}
                  </p>
                  <p className="mt-2 font-medium text-[#0F172A]">{v}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <CTABanner
        title="Want to know if we're the right partner?"
        subtitle="A 30-minute conversation will tell us both. No pitch, no obligation."
      />
      <div className="h-24" />
    </>
  );
}

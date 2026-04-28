import Reveal from "@/components/Reveal";
import SectionHeading from "@/components/SectionHeading";
import CTABanner from "@/components/CTABanner";
import { Building2, HeartPulse, GraduationCap, Landmark, Factory } from "lucide-react";
import { INDUSTRIES } from "@/data/site";

const ICONS = {
  "financial-services": Building2,
  healthcare: HeartPulse,
  education: GraduationCap,
  government: Landmark,
  manufacturing: Factory,
};

export default function Industries() {
  return (
    <>
      <section className="section pt-16">
        <div className="container-x">
          <SectionHeading
            eyebrow="Industries"
            title="Built for environments where stakes — and stigma — are highest."
            description="Our work is shaped by the realities of regulated, frontline and high-pressure sectors. Below are the contexts we know best."
            testid="industries-heading"
          />
        </div>
      </section>

      <section className="container-x">
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {INDUSTRIES.map((ind, i) => {
            const Icon = ICONS[ind.slug];
            return (
              <Reveal key={ind.slug} delay={i * 0.05}>
                <div
                  data-testid={`industry-card-${ind.slug}`}
                  className="bg-white border border-slate-100 rounded-2xl p-8 h-full hover:-translate-y-1 hover:shadow-[0_18px_36px_-15px_rgba(28,63,58,0.18)] transition-all"
                >
                  <div className="w-12 h-12 rounded-xl bg-[#F1F5F2] flex items-center justify-center text-[#1C3F3A]">
                    <Icon size={22} />
                  </div>
                  <h3 className="mt-6 text-2xl font-medium text-[#0F172A]">
                    {ind.title}
                  </h3>
                  <p className="mt-3 text-[#475569] leading-relaxed">
                    {ind.body}
                  </p>
                </div>
              </Reveal>
            );
          })}
        </div>
      </section>

      <div className="h-24" />

      <section className="section bg-[#F1F5F2]">
        <div className="container-x grid md:grid-cols-12 gap-10 items-start">
          <div className="md:col-span-5">
            <SectionHeading
              eyebrow="How we adapt"
              title="Same framework, calibrated to your context."
              description="An EAP for a hospital looks nothing like an EAP for a mine. We tailor language, modality, schedule and reporting to where your people actually work."
            />
          </div>
          <div className="md:col-span-7 grid md:grid-cols-2 gap-4">
            {[
              ["Frontline shift cover", "EAP & critical-incident response built around 24/7 rotations."],
              ["Regulator-ready evidence", "Audit-trail reporting that maps cleanly to risk registers."],
              ["Multilingual delivery", "Setswana, English and major SADC languages on call."],
              ["Anonymity by default", "Clinical confidentiality is non-negotiable. Always."],
            ].map(([k, v]) => (
              <Reveal key={k}>
                <div className="bg-white rounded-xl p-6">
                  <p className="font-medium text-[#0F172A]">{k}</p>
                  <p className="mt-2 text-sm text-[#475569] leading-relaxed">{v}</p>
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

import SectionHeading from "@/components/SectionHeading";
import SEO from "@/components/SEO";
import { SITE } from "@/data/site";

export default function Disclaimer() {
  return (
    <>
      <SEO title="Clinical & Safety Disclaimer" path="/disclaimer" />
      <div className="section container-x max-w-4xl py-16 space-y-8 text-sm text-[#475569] leading-relaxed">
        <SectionHeading
          eyebrow="Clinical Governance"
          title="Clinical & Safety Disclaimer"
          description="Important information regarding the scope and boundaries of FCA services."
        />
        <div className="space-y-6 bg-white p-8 sm:p-12 rounded-3xl border border-slate-200 shadow-sm">
          <section className="space-y-2">
            <h2 className="text-lg font-bold text-[#0F172A]">1. Outpatient Scope</h2>
            <p>
              Foundations Counselling Academy operates as an outpatient counselling, corporate wellbeing, and educational training organisation. Information published on this website does not substitute for personalized medical diagnosis or psychiatric emergency intervention.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-bold text-[#0F172A]">2. Emergency Situations</h2>
            <p>
              FCA is <strong>not an emergency rescue service</strong>. If you or someone you are concerned about is in immediate danger of self-harm, physical violence, or acute crisis, please contact Botswana Emergency Services by dialing <strong>999</strong> immediately or visit your nearest hospital casualty department.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-bold text-[#0F172A]">3. Confidentiality Limits</h2>
            <p>
              All counselling sessions are strictly confidential within professional ethical boundaries. By law, confidentiality may be broken if there is clear evidence of imminent risk of severe harm to self or others, or child abuse.
            </p>
          </section>
        </div>
      </div>
    </>
  );
}

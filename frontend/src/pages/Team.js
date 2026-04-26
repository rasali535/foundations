import Reveal from "@/components/Reveal";
import SectionHeading from "@/components/SectionHeading";
import CTABanner from "@/components/CTABanner";
import { TEAM } from "@/data/site";

export default function Team() {
  return (
    <>
      <section className="section pt-16">
        <div className="container-x">
          <SectionHeading
            eyebrow="Team"
            title="Senior practitioners. Africa-rooted. Globally trained."
            description="A small, accountable team — every engagement is led by someone you'll meet in the first scoping call."
            testid="team-heading"
          />
        </div>
      </section>

      <section className="container-x">
        <div className="grid md:grid-cols-3 gap-6">
          {TEAM.map((m, i) => (
            <Reveal key={m.name} delay={i * 0.05}>
              <article
                data-testid={`team-card-${i}`}
                className="bg-white border border-slate-100 rounded-2xl overflow-hidden h-full hover:-translate-y-1 hover:shadow-[0_18px_36px_-15px_rgba(28,63,58,0.18)] transition-all"
              >
                <div className="aspect-[4/5] overflow-hidden">
                  <img
                    src={m.img}
                    alt={m.name}
                    className="w-full h-full object-cover"
                  />
                </div>
                <div className="p-7">
                  <p className="eyebrow">{m.role}</p>
                  <h3 className="mt-3 text-2xl font-medium text-[#0F172A]">
                    {m.name}
                  </h3>
                  <p className="mt-2 text-sm text-[#81B29A]">{m.creds}</p>
                  <p className="mt-4 text-[#475569] leading-relaxed text-sm">
                    {m.bio}
                  </p>
                </div>
              </article>
            </Reveal>
          ))}
        </div>
      </section>

      <div className="h-24" />

      <section className="section bg-[#F1F5F2]">
        <div className="container-x grid md:grid-cols-12 gap-10 items-start">
          <div className="md:col-span-5">
            <SectionHeading
              eyebrow="Bench & associates"
              title="Plus a vetted bench for scale."
              description="For larger engagements we draw on a vetted bench of associate clinicians, coaches and facilitators across Botswana and the broader SADC region — all selected against the same clinical and ethical standard."
            />
          </div>
          <div className="md:col-span-7 grid md:grid-cols-2 gap-4">
            {[
              ["Clinical psychologists", "Trauma-informed and supervised."],
              ["Industrial psychologists", "Diagnostic, assessment and ODD."],
              ["Executive coaches", "ICF-credentialed where applicable."],
              ["Facilitators", "Workshop, training and capability build."],
            ].map(([k, v]) => (
              <Reveal key={k}>
                <div className="bg-white rounded-xl p-6">
                  <p className="font-medium text-[#0F172A]">{k}</p>
                  <p className="mt-2 text-sm text-[#475569]">{v}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <CTABanner
        title="Want to meet the lead consultant for your sector?"
        subtitle="Book a scoping call and we'll match you with the right practitioner."
      />
      <div className="h-24" />
    </>
  );
}

import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import Reveal from "@/components/Reveal";
import SectionHeading from "@/components/SectionHeading";
import CTABanner from "@/components/CTABanner";
import { SERVICES } from "@/data/site";

export default function Services() {
  return (
    <>
      <section className="section pt-16">
        <div className="container-x">
          <SectionHeading
            eyebrow="Services"
            title="Four practices. One operating system for workplace wellbeing."
            description="Each service is delivered as a standalone engagement or stitched together into a single, measurable programme that runs across your business."
            testid="services-heading"
          />
        </div>
      </section>

      <section className="container-x">
        <div className="grid gap-6">
          {SERVICES.map((s, i) => (
            <Reveal key={s.slug} delay={i * 0.05}>
              <Link
                to={`/services/${s.slug}`}
                data-testid={`services-card-${s.slug}`}
                className="group grid md:grid-cols-12 gap-8 items-stretch bg-white border border-slate-100 rounded-2xl overflow-hidden hover:-translate-y-1 hover:shadow-[0_24px_48px_-20px_rgba(28,63,58,0.18)] transition-all"
              >
                <div className="md:col-span-5 relative h-64 md:h-auto overflow-hidden">
                  <img
                    src={s.image}
                    alt={s.title}
                    className="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                  />
                  <span className="absolute top-5 left-5 text-[10px] uppercase tracking-[0.2em] bg-white/90 text-[#1C3F3A] px-3 py-1.5 rounded-full">
                    {s.category}
                  </span>
                </div>
                <div className="md:col-span-7 p-8 md:p-12 flex flex-col justify-center">
                  <p className="eyebrow">{`0${i + 1}`}</p>
                  <h3 className="mt-3 text-3xl font-semibold tracking-tight text-[#0F172A]">
                    {s.title}
                  </h3>
                  <p className="mt-4 text-[#475569] leading-relaxed">
                    {s.short}
                  </p>
                  <span className="mt-6 inline-flex items-center gap-2 text-[#1C3F3A] font-medium group-hover:gap-3 transition-all">
                    Service detail <ArrowRight size={16} />
                  </span>
                </div>
              </Link>
            </Reveal>
          ))}
        </div>
      </section>

      <div className="h-24" />
      <CTABanner />
      <div className="h-24" />
    </>
  );
}

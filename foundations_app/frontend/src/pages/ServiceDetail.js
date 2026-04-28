import { useParams, Link } from "react-router-dom";
import { ArrowLeft, CheckCircle2, ArrowRight } from "lucide-react";
import Reveal from "@/components/Reveal";
import SectionHeading from "@/components/SectionHeading";
import CTABanner from "@/components/CTABanner";
import { SERVICES } from "@/data/site";

export default function ServiceDetail() {
  const { slug } = useParams();
  const service = SERVICES.find((s) => s.slug === slug);

  if (!service) {
    return (
      <section className="section container-x">
        <p className="text-[#475569]">Service not found.</p>
        <Link to="/services" className="btn-ghost mt-6 inline-flex">
          <ArrowLeft size={16} /> Back to services
        </Link>
      </section>
    );
  }

  return (
    <>
      <section className="section pt-16">
        <div className="container-x">
          <Link
            to="/services"
            className="inline-flex items-center gap-2 text-[#475569] hover:text-[#1C3F3A] text-sm mb-8"
          >
            <ArrowLeft size={16} /> Back to services
          </Link>
          <div className="grid md:grid-cols-12 gap-10 items-end">
            <div className="md:col-span-8">
              <p className="eyebrow">{service.category}</p>
              <h1 className="mt-4 text-4xl sm:text-5xl lg:text-7xl font-semibold tracking-tight leading-[1.05] text-[#0F172A]">
                {service.title}
              </h1>
              <p className="mt-6 text-lg text-[#475569] leading-relaxed max-w-2xl">
                {service.description || service.short}
              </p>
            </div>
            <div className="md:col-span-4 hidden md:block">
              <div className="aspect-[4/3] rounded-2xl overflow-hidden border border-slate-100">
                <img
                  src={service.image}
                  alt={service.title}
                  className="w-full h-full object-cover"
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section pt-0">
        <div className="container-x grid md:grid-cols-12 gap-12">
          <div className="md:col-span-7">
            <h2 className="text-2xl font-semibold text-[#0F172A] mb-8">
              Key outcomes
            </h2>
            <ul className="space-y-4">
              {(service.outcomes || [
                "Reduced psychosocial risk and liability.",
                "Improved leader confidence in mental health.",
                "Board-ready impact reporting.",
                "Culture of psychological safety."
              ]).map((o) => (
                <li key={o} className="flex items-start gap-3 text-[#0F172A]">
                  <CheckCircle2
                    size={22}
                    className="text-[#81B29A] mt-0.5 flex-shrink-0"
                  />
                  <span className="text-lg leading-relaxed">{o}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="md:col-span-5">
            <div className="bg-[#F1F5F2] border border-[#E2E8F0] rounded-2xl p-8">
              <h3 className="text-xl font-semibold text-[#0F172A]">
                Delivery details
              </h3>
              <p className="mt-4 text-[#475569] text-sm leading-relaxed">
                Every {service.title} engagement follows our Four Pillars
                Framework, ensuring that interventions aren't just one-offs, but
                part of a sustainable system.
              </p>
              <Link to="/approach" className="mt-6 inline-flex items-center gap-2 text-[#1C3F3A] font-medium text-sm">
                View our approach <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        </div>
      </section>

      <CTABanner
        title={`Ready to scope a ${service.title} programme?`}
        subtitle="Book a consultation with our senior clinical team to discuss your specific needs."
      />
      <div className="h-24" />
    </>
  );
}

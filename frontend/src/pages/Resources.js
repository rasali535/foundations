import { FileText, ArrowUpRight, Download, Sparkles, CheckCircle2 } from "lucide-react";
import SectionHeading from "@/components/SectionHeading";
import SEO from "@/components/SEO";
import { RESOURCES_LIST, FEATURED_OFFER } from "@/data/site";

export default function Resources() {
  return (
    <>
      <SEO
        title="Resources & Wellbeing Toolkits"
        description="Downloadable mental fitness guides, burnout recovery planners, and workplace psychological safety frameworks from Foundations Counselling Academy."
        path="/resources"
      />

      <section className="section bg-[#FAFAFA] pt-16 pb-20 border-b border-slate-200/60">
        <div className="container-x">
          <SectionHeading
            eyebrow="Evidence-Led Toolkits"
            title="Practical resources to regulate stress and build steady momentum."
            description="Download our free self-reflection workbooks, executive audit checklists, and manager guides."
          />

          {/* Featured 7-Day Steadiness Planner */}
          <div className="mt-12 bg-white rounded-3xl p-8 sm:p-12 border border-slate-200/80 shadow-sm grid lg:grid-cols-12 gap-8 items-center">
            <div className="lg:col-span-8 space-y-4">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#D4A373]/20 text-xs font-bold text-[#1C3F3A]">
                <Sparkles size={13} />
                <span>{FEATURED_OFFER.badge}</span>
              </div>
              <h2 className="text-3xl font-bold text-[#0F172A]">
                {FEATURED_OFFER.title}
              </h2>
              <p className="text-base text-[#475569] leading-relaxed">
                {FEATURED_OFFER.description}
              </p>
              <div className="pt-2">
                <a
                  href={FEATURED_OFFER.kajabi_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-primary inline-flex items-center gap-2"
                >
                  <Download size={16} />
                  <span>{FEATURED_OFFER.cta_text}</span>
                </a>
              </div>
            </div>
            <div className="lg:col-span-4 bg-[#1C3F3A] text-white p-6 rounded-2xl text-center space-y-2">
              <FileText size={36} className="mx-auto text-[#D4A373]" />
              <p className="font-bold">Instant Free Access</p>
              <p className="text-xs text-white/70">Delivered via our secure member portal.</p>
            </div>
          </div>

          {/* Resource Catalog */}
          <div className="mt-16">
            <h3 className="text-2xl font-bold text-[#0F172A] mb-8">All Guides & Frameworks</h3>
            <div className="grid md:grid-cols-3 gap-6">
              {RESOURCES_LIST.map((r) => (
                <div key={r.slug} className="bg-white rounded-2xl p-7 border border-slate-200/80 space-y-4 flex flex-col justify-between shadow-sm">
                  <div className="space-y-3">
                    <span className="text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded-full bg-[#FAFAFA] text-[#1C3F3A] border border-slate-200">
                      {r.badge}
                    </span>
                    <h4 className="text-lg font-bold text-[#0F172A]">{r.title}</h4>
                    <p className="text-xs text-[#81B29A] font-semibold">{r.type}</p>
                    <p className="text-sm text-[#475569] leading-relaxed">{r.description}</p>
                  </div>
                  <div className="pt-4 border-t border-slate-100">
                    <a
                      href={r.link}
                      className="text-xs font-bold text-[#1C3F3A] hover:underline flex items-center justify-between"
                    >
                      <span>Access Resource</span>
                      <ArrowUpRight size={14} />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

import { Link } from "react-router-dom";
import { Users, Sparkles, CheckCircle2, ArrowRight, ArrowUpRight, MessageCircle } from "lucide-react";
import SectionHeading from "@/components/SectionHeading";
import SEO from "@/components/SEO";
import { SITE, getWhatsAppUrl, COURSES } from "@/data/site";

export default function TrainingTeamBuilding() {
  return (
    <>
      <SEO
        title="Training & Team Building"
        description="High-impact corporate team building retreats, resilience workshops, and leadership development programmes in Botswana."
        path="/training-team-building"
      />

      {/* Hero */}
      <section className="section bg-[#FAFAFA] pt-16 pb-20 border-b border-slate-200/60">
        <div className="container-x grid lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-8 space-y-6">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#D4A373]/20 text-xs font-semibold uppercase tracking-wider text-[#1C3F3A]">
              <Users size={14} />
              <span>Experiential Team Building & Corporate Training</span>
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-[#0F172A] tracking-tight leading-[1.08]">
              High-impact team building & <span className="text-[#1C3F3A]">resilient team development.</span>
            </h1>
            <p className="text-lg text-[#475569] max-w-2xl leading-relaxed">
              We design and facilitate experiential team building retreats, mental fitness workshops, and communication training that transform workplace culture and elevate team performance.
            </p>
            <div className="flex flex-wrap gap-4 pt-2">
              <Link
                to="/contact"
                data-testid="training-quote-btn"
                className="btn-primary flex items-center gap-2 shadow-md"
              >
                <span>Request a Customised Quote</span>
                <ArrowRight size={16} />
              </Link>
              <a
                href={getWhatsAppUrl("training")}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-ghost flex items-center gap-2"
              >
                <MessageCircle size={16} />
                <span>Discuss via WhatsApp</span>
              </a>
            </div>
          </div>

          <div className="lg:col-span-4 bg-white rounded-3xl p-8 border border-slate-200 space-y-4 shadow-sm">
            <p className="text-xs font-bold uppercase tracking-widest text-[#1C3F3A]">Delivery Formats</p>
            <ul className="space-y-3 text-sm text-[#475569]">
              <li className="flex items-start gap-2">
                <CheckCircle2 size={16} className="text-[#81B29A] mt-0.5 flex-shrink-0" />
                <span><strong>Off-Site Team Retreats:</strong> Full-day & multi-day immersive team building.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 size={16} className="text-[#81B29A] mt-0.5 flex-shrink-0" />
                <span><strong>On-Site Workshops:</strong> Interactive 2–4 hour modular sessions in your office.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 size={16} className="text-[#81B29A] mt-0.5 flex-shrink-0" />
                <span><strong>Virtual Cohorts:</strong> Live interactive workshops for distributed teams.</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* FEATURED: EXPERIENTIAL TEAM BUILDING */}
      <section className="section bg-white">
        <div className="container-x">
          <div className="bg-[#1C3F3A] text-white rounded-3xl p-8 sm:p-12 grid lg:grid-cols-12 gap-8 items-center">
            <div className="lg:col-span-8 space-y-4">
              <span className="text-xs uppercase tracking-widest text-[#D4A373] font-bold">Featured Flagship</span>
              <h2 className="text-3xl font-bold">Experiential Team Building Retreats</h2>
              <p className="text-white/80 text-sm leading-relaxed max-w-2xl">
                Unlike superficial entertainment outings, FCA team building is structured by behavioural specialists to diagnose interpersonal bottlenecks, rebuild trust, foster psychological safety, and align collective focus on key organizational milestones.
              </p>
              <div className="pt-2 flex flex-wrap gap-4">
                <Link to="/contact" className="px-6 py-3 rounded-full bg-[#D4A373] text-[#1C3F3A] font-bold text-xs hover:bg-white transition-colors">
                  Plan Your Team Retreat
                </Link>
              </div>
            </div>
            <div className="lg:col-span-4 bg-white/10 rounded-2xl p-6 border border-white/10 space-y-2 text-xs text-white/80">
              <p className="font-semibold text-white">Ideal for:</p>
              <p>• Executive leadership teams</p>
              <p>• Cross-functional project units</p>
              <p>• Teams undergoing rapid change/restructuring</p>
              <p>• Annual strategy alignment retreats</p>
            </div>
          </div>
        </div>
      </section>

      {/* TRAINING WORKSHOPS CATALOG */}
      <section className="section bg-[#F1F5F2]">
        <div className="container-x">
          <SectionHeading
            eyebrow="Corporate Workshop Catalogue"
            title="Evidence-led workplace training modules."
            description="Facilitated by certified clinicians and organisational development specialists."
          />

          <div className="mt-12 grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {COURSES.map((c) => (
              <div key={c.slug} className="bg-white rounded-2xl p-7 border border-slate-200/80 space-y-4 flex flex-col justify-between shadow-sm">
                <div className="space-y-3">
                  <span className="text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded-full bg-[#FAFAFA] text-[#1C3F3A] border border-slate-200">
                    {c.category}
                  </span>
                  <h3 className="text-xl font-bold text-[#0F172A]">{c.title}</h3>
                  <p className="text-sm text-[#475569] leading-relaxed">{c.summary}</p>
                </div>
                <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-xs text-[#81B29A] font-semibold">{c.cpd}</span>
                  <Link to={`/learning/${c.slug}`} className="text-xs font-bold text-[#1C3F3A] hover:underline flex items-center gap-1">
                    <span>Preview Syllabus</span>
                    <ArrowUpRight size={13} />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Quote Banner */}
      <section className="section bg-white text-center">
        <div className="container-x max-w-3xl space-y-6">
          <h2 className="text-3xl font-bold text-[#0F172A]">Need a custom curriculum for your organisation?</h2>
          <p className="text-[#475569] text-base">
            We adapt case studies, group exercises, and delivery schedules to your industry context.
          </p>
          <div>
            <Link to="/contact" className="btn-primary inline-flex items-center gap-2">
              <span>Request a Customised Quote</span>
              <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}

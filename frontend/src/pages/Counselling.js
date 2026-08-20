import { Link } from "react-router-dom";
import { MessageCircle, Phone, Clock, MapPin, ShieldCheck, HeartPulse, CheckCircle2, AlertTriangle, ArrowRight } from "lucide-react";
import Reveal from "@/components/Reveal";
import SectionHeading from "@/components/SectionHeading";
import SEO from "@/components/SEO";
import { SITE, getWhatsAppUrl } from "@/data/site";

export default function Counselling() {
  return (
    <>
      <SEO
        title="Personal & Couples Counselling"
        description="Warm, confidential, and professional counselling in Gaborone and virtual therapy across Botswana. Individual therapy, couples counselling, and family support."
        path="/counselling"
      />

      {/* Hero */}
      <section className="section bg-[#FAFAFA] pt-16 pb-14 border-b border-slate-200/60">
        <div className="container-x grid lg:grid-cols-12 gap-10 items-center">
          <div className="lg:col-span-8 space-y-5">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#81B29A]/20 text-[#1C3F3A] text-xs font-semibold uppercase tracking-wider">
              <HeartPulse size={14} />
              <span>Compassionate · Confidential · Evidence-Led</span>
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-[#0F172A] tracking-tight leading-tight">
              Personal, couples and family counselling.
            </h1>
            <p className="text-lg text-[#475569] max-w-2xl leading-relaxed">
              A private, supportive environment to help you work through anxiety, relationship conflict, life transitions, grief, and workplace burnout with experienced clinicians.
            </p>
            <div className="flex flex-wrap gap-4 pt-2">
              <a
                href={getWhatsAppUrl("counselling")}
                target="_blank"
                rel="noopener noreferrer"
                data-testid="counselling-whatsapp-primary"
                className="btn-primary flex items-center gap-2 shadow-md"
              >
                <MessageCircle size={18} />
                <span>Book / Enquire via WhatsApp</span>
              </a>
              <a
                href={`tel:${SITE.phone.replace(/\s+/g, "")}`}
                className="btn-ghost flex items-center gap-2"
              >
                <Phone size={16} />
                <span>Call FCA ({SITE.phone})</span>
              </a>
            </div>
          </div>

          <div className="lg:col-span-4 bg-white rounded-3xl border border-slate-200/80 p-6 space-y-4 shadow-sm">
            <p className="text-xs font-bold uppercase tracking-widest text-[#1C3F3A]">Quick Facts</p>
            <div className="space-y-3 text-sm text-[#475569]">
              <div className="flex items-start gap-2.5">
                <Clock size={16} className="text-[#D4A373] mt-0.5 flex-shrink-0" />
                <span><strong>Duration:</strong> 50–60 minute structured sessions</span>
              </div>
              <div className="flex items-start gap-2.5">
                <MapPin size={16} className="text-[#D4A373] mt-0.5 flex-shrink-0" />
                <span><strong>Location:</strong> Plot 18680 Khuhurutse St, Phase 2, Gaborone (or secure virtual sessions)</span>
              </div>
              <div className="flex items-start gap-2.5">
                <ShieldCheck size={16} className="text-[#D4A373] mt-0.5 flex-shrink-0" />
                <span><strong>Hours:</strong> Mon–Fri 09:00–17:00 · Sat 09:00–13:00 <em className="text-xs text-slate-400 block">(Subject to confirmation)</em></span>
              </div>
            </div>
            <div className="pt-2 border-t border-slate-100">
              <Link to="/intake" className="text-xs font-semibold text-[#1C3F3A] hover:underline flex items-center gap-1">
                <span>Go to Confidential Intake Portal</span>
                <ArrowRight size={13} />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Therapy Modalities */}
      <section className="section bg-white">
        <div className="container-x">
          <SectionHeading
            eyebrow="Areas of Support"
            title="How we support you and your family."
            description="Our clinical practice covers structured, solution-oriented counselling tailored to your unique circumstances."
          />

          <div className="mt-12 grid md:grid-cols-3 gap-8">
            <div className="p-7 rounded-2xl bg-[#FAFAFA] border border-slate-200/80 space-y-3">
              <h3 className="text-xl font-bold text-[#0F172A]">Individual Counselling</h3>
              <p className="text-sm text-[#475569] leading-relaxed">
                Dedicated 1-on-1 sessions focused on anxiety, depression, workplace stress, grief, trauma recovery, and personal boundary setting.
              </p>
              <ul className="space-y-2 text-xs text-[#0F172A] pt-2">
                <li>• Stress regulation & burnout</li>
                <li>• Emotional regulation (CBT principles)</li>
                <li>• Major life transitions</li>
              </ul>
            </div>

            <div className="p-7 rounded-2xl bg-[#FAFAFA] border border-slate-200/80 space-y-3">
              <h3 className="text-xl font-bold text-[#0F172A]">Couples & Marriage</h3>
              <p className="text-sm text-[#475569] leading-relaxed">
                Constructive relationship support to improve communication, rebuild broken trust, resolve chronic conflict, and restore emotional intimacy.
              </p>
              <ul className="space-y-2 text-xs text-[#0F172A] pt-2">
                <li>• Communication breakdowns</li>
                <li>• Rebuilding trust after infidelity</li>
                <li>• Pre-marital counselling</li>
              </ul>
            </div>

            <div className="p-7 rounded-2xl bg-[#FAFAFA] border border-slate-200/80 space-y-3">
              <h3 className="text-xl font-bold text-[#0F172A]">Family & Parenting</h3>
              <p className="text-sm text-[#475569] leading-relaxed">
                Helping parents and families navigate adolescent behaviour, blended family dynamics, bereavement, and generational communication barriers.
              </p>
              <ul className="space-y-2 text-xs text-[#0F172A] pt-2">
                <li>• Parent-child dynamics</li>
                <li>• Adolescent emotional support</li>
                <li>• Family bereavement counselling</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Appointment Process Flow */}
      <section className="section bg-[#F1F5F2]">
        <div className="container-x">
          <SectionHeading
            eyebrow="Our Process"
            title="How counselling appointments work."
            description="From initial enquiry to confidential session, our booking journey is clear and private."
            center
          />

          <div className="mt-12 grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-white p-6 rounded-2xl border border-slate-200/70 space-y-2">
              <span className="text-2xl font-bold text-[#D4A373]">01</span>
              <h4 className="font-bold text-[#0F172A]">Enquire via WhatsApp</h4>
              <p className="text-xs text-[#475569]">Send a brief message to our coordinator regarding your interest in therapy.</p>
            </div>
            <div className="bg-white p-6 rounded-2xl border border-slate-200/70 space-y-2">
              <span className="text-2xl font-bold text-[#D4A373]">02</span>
              <h4 className="font-bold text-[#0F172A]">Availability & Rates</h4>
              <p className="text-xs text-[#475569]">FCA confirms therapist availability and outlines rates confidentially.</p>
            </div>
            <div className="bg-white p-6 rounded-2xl border border-slate-200/70 space-y-2">
              <span className="text-2xl font-bold text-[#D4A373]">03</span>
              <h4 className="font-bold text-[#0F172A]">Secure Intake</h4>
              <p className="text-xs text-[#475569]">Complete your private intake questionnaire and safety review prior to session.</p>
            </div>
            <div className="bg-white p-6 rounded-2xl border border-slate-200/70 space-y-2">
              <span className="text-2xl font-bold text-[#D4A373]">04</span>
              <h4 className="font-bold text-[#0F172A]">Attend Your Session</h4>
              <p className="text-xs text-[#475569]">Meet your counsellor in Phase 2 Gaborone or via secure virtual link.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Emergency & Confidentiality Notice */}
      <section className="section bg-white border-t border-slate-200/60">
        <div className="container-x max-w-4xl bg-[#FFFBEB] border border-[#FDE68A] rounded-2xl p-8 space-y-4">
          <div className="flex items-center gap-2 text-[#92400E] font-bold">
            <AlertTriangle size={20} />
            <span>Important Safety & Clinical Advisory</span>
          </div>
          <p className="text-sm text-[#78350F] leading-relaxed">
            Foundations Counselling Academy operates as an outpatient therapy practice and is <strong>not an emergency crisis response unit</strong>. 
            If you or someone in your care is experiencing an immediate life-threatening crisis, suicidal intent, or physical harm, please immediately contact Botswana Emergency Services by dialing <strong>999</strong> or visit your nearest hospital emergency ward.
          </p>
        </div>
      </section>

      {/* Final Action */}
      <section className="section bg-[#1C3F3A] text-white text-center">
        <div className="container-x max-w-2xl space-y-6">
          <h2 className="text-3xl font-bold">Ready to take the next step?</h2>
          <p className="text-white/80 text-sm">
            Reach out today. Our team will handle your enquiry with strict professional confidentiality.
          </p>
          <div className="flex justify-center gap-4 pt-2">
            <a
              href={getWhatsAppUrl("counselling")}
              target="_blank"
              rel="noopener noreferrer"
              className="px-8 py-3.5 rounded-full bg-[#D4A373] text-[#1C3F3A] font-bold text-sm hover:bg-white transition-colors"
            >
              Enquire on WhatsApp
            </a>
          </div>
        </div>
      </section>
    </>
  );
}

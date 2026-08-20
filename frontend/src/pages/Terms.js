import SectionHeading from "@/components/SectionHeading";
import SEO from "@/components/SEO";
import { SITE } from "@/data/site";

export default function Terms() {
  return (
    <>
      <SEO title="Terms of Service" path="/terms" />
      <div className="section container-x max-w-4xl py-16 space-y-8 text-sm text-[#475569] leading-relaxed">
        <SectionHeading
          eyebrow="Legal"
          title="Terms of Service"
          description="Standard terms governing website usage, consultation bookings, and online masterclasses."
        />
        <div className="space-y-6 bg-white p-8 sm:p-12 rounded-3xl border border-slate-200 shadow-sm">
          <section className="space-y-2">
            <h2 className="text-lg font-bold text-[#0F172A]">1. Agreement to Terms</h2>
            <p>
              These Terms of Service constitute a legally binding agreement between you and {SITE.name} ({SITE.parent}), located at {SITE.address}. By accessing our website or utilizing our counselling and training services, you agree to be bound by these terms.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-bold text-[#0F172A]">2. Professional Services Scope</h2>
            <p>
              FCA provides structured outpatient personal counselling, employee assistance programmes (EAP), corporate training, and digital educational masterclasses. FCA is not a medical facility or emergency psychiatric service.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-bold text-[#0F172A]">3. Appointment Booking & Cancellation</h2>
            <p>
              Counselling appointments and corporate workshops are confirmed upon direct agreement with FCA coordinators. Cancellations requested less than 24 hours before a scheduled session may be subject to a cancellation fee.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-bold text-[#0F172A]">4. Intellectual Property</h2>
            <p>
              All course materials, workbooks, diagnostics, and brand assets displayed on {SITE.canonicalUrl} or our Kajabi learning portal are the proprietary intellectual property of {SITE.name}.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-bold text-[#0F172A]">5. Governing Law</h2>
            <p>
              These terms are governed by and construed in accordance with the laws of the Republic of Botswana.
            </p>
          </section>
        </div>
      </div>
    </>
  );
}

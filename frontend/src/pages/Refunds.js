import SectionHeading from "@/components/SectionHeading";
import SEO from "@/components/SEO";
import { SITE } from "@/data/site";

export default function Refunds() {
  return (
    <>
      <SEO title="Refund & Cancellation Policy" path="/refunds" />
      <div className="section container-x max-w-4xl py-16 space-y-8 text-sm text-[#475569] leading-relaxed">
        <SectionHeading
          eyebrow="Billing"
          title="Refund & Cancellation Policy"
          description="Guidelines regarding cancellations, session rescheduling, and online programme enrollments."
        />
        <div className="space-y-6 bg-white p-8 sm:p-12 rounded-3xl border border-slate-200 shadow-sm">
          <section className="space-y-2">
            <h2 className="text-lg font-bold text-[#0F172A]">1. Counselling Appointments</h2>
            <p>
              Individual and couples counselling sessions may be rescheduled without charge if notification is provided at least 24 hours prior to the appointment. Missed appointments without notice may be charged at the standard rate.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-bold text-[#0F172A]">2. Online Programmes (Kajabi Hub)</h2>
            <p>
              Digital masterclasses and workbooks purchased via the Kajabi member portal offer a 14-day satisfaction guarantee, provided less than 25% of course content has been accessed.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-bold text-[#0F172A]">3. Corporate Training & Retreats</h2>
            <p>
              Corporate workshop and team building cancellations are governed by the specific service level agreement (SLA) signed with your organisation.
            </p>
          </section>
        </div>
      </div>
    </>
  );
}

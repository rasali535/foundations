import SectionHeading from "@/components/SectionHeading";
import SEO from "@/components/SEO";
import { SITE } from "@/data/site";

export default function Cookies() {
  return (
    <>
      <SEO title="Cookie Notice" path="/cookies" />
      <div className="section container-x max-w-4xl py-16 space-y-8 text-sm text-[#475569] leading-relaxed">
        <SectionHeading
          eyebrow="Privacy"
          title="Cookie Notice"
          description="How Foundations Counselling Academy uses cookies and local storage."
        />
        <div className="space-y-6 bg-white p-8 sm:p-12 rounded-3xl border border-slate-200 shadow-sm">
          <section className="space-y-2">
            <h2 className="text-lg font-bold text-[#0F172A]">1. What Are Cookies</h2>
            <p>
              Cookies are small text files stored on your device that help web applications remember user preferences and maintain secure session states.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-bold text-[#0F172A]">2. Essential Cookies We Use</h2>
            <p>
              We use strictly necessary cookies for session management (e.g. `fca_session_id` with HttpOnly and SameSite=Lax attributes) and anonymous aggregate analytics through Google Analytics (GA4).
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-bold text-[#0F172A]">3. Zero Clinical Data Tracking</h2>
            <p>
              Cookies are never used to track clinical intake answers, therapy history, or sensitive personal health details.
            </p>
          </section>
        </div>
      </div>
    </>
  );
}

import Reveal from "@/components/Reveal";
import { SITE } from "@/data/site";

export default function Privacy() {
  return (
    <section className="section pt-16">
      <div className="container-x max-w-3xl">
        <Reveal>
          <p className="eyebrow">Legal</p>
          <h1 className="mt-3 text-4xl sm:text-5xl font-semibold tracking-tight text-[#0F172A]">
            Privacy Policy
          </h1>
          <p className="mt-4 text-sm text-[#475569]">
            Last updated: {new Date().toLocaleDateString("en-GB", { year: "numeric", month: "long" })}
          </p>
        </Reveal>

        <Reveal delay={0.05}>
          <div className="mt-12 space-y-8 text-[#0F172A] leading-relaxed">
            <Block title="1. Who we are">
              {SITE.name}, a {SITE.parent}, registered in Botswana. Contact:{" "}
              <a className="underline" href={`mailto:${SITE.email}`}>
                {SITE.email}
              </a>
              .
            </Block>

            <Block title="2. What we collect">
              We collect only what is necessary to respond to your enquiry or
              deliver our services. This includes your name, work email,
              company, phone number, inquiry type and any details you choose to
              share via our contact form or chatbot.
            </Block>

            <Block title="3. Why we collect it">
              To respond to enquiries, schedule consultations, deliver
              contracted services and meet our legal and contractual
              obligations.
            </Block>

            <Block title="4. How we store it">
              Your data is stored on access-controlled, encrypted infrastructure.
              Access is limited to consultants directly involved in your
              engagement. Clinical records, where applicable, are held under
              additional confidentiality controls in line with professional
              practice standards.
            </Block>

            <Block title="5. Sharing">
              We do not sell or rent personal information. We share data only
              with sub-processors strictly necessary to deliver our services
              (e.g. secure email and chat hosting), each bound by appropriate
              data-protection agreements.
            </Block>

            <Block title="6. Your rights">
              You may request access, correction, or deletion of your personal
              information at any time by emailing{" "}
              <a className="underline" href={`mailto:${SITE.email}`}>
                {SITE.email}
              </a>
              . We will respond within 30 days.
            </Block>

            <Block title="7. Chatbot interactions">
              Conversations with our chatbot, Aliana, are stored to improve service
              quality and route follow-up. We do not use them for advertising
              and we do not share them with third parties beyond what is
              described above.
            </Block>

            <Block title="8. Updates">
              We may update this policy from time to time. Material changes will
              be communicated via this page.
            </Block>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

function Block({ title, children }) {
  return (
    <div>
      <h2 className="text-xl font-semibold text-[#0F172A]">{title}</h2>
      <p className="mt-3 text-[#475569]">{children}</p>
    </div>
  );
}

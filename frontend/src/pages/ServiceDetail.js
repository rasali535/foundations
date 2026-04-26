import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Check } from "lucide-react";
import Reveal from "@/components/Reveal";
import CTABanner from "@/components/CTABanner";
import { SERVICES } from "@/data/site";

export default function ServiceDetail() {
  const { slug } = useParams();
  const s = SERVICES.find((x) => x.slug === slug);
  if (!s) {
    return (
      <section className="section container-x">
        <p className="text-[#475569]">Service not found.</p>
        <Link to="/services" className="btn-ghost mt-6 inline-flex">
          <ArrowLeft size={16} /> Back to services
        </Link>
      </section>
    );
  }

  const others = SERVICES.filter((x) => x.slug !== s.slug);

  return (
    <>
      <section className="relative h-[58vh] min-h-[420px] overflow-hidden">
        <img
          src={s.image}
          alt={s.title}
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#1C3F3A]/85 via-[#1C3F3A]/45 to-transparent" />
        <div className="relative container-x h-full flex flex-col justify-end pb-14 text-white">
          <Reveal>
            <p className="eyebrow text-white/80">{s.category} · Service</p>
          </Reveal>
          <Reveal delay={0.05}>
            <h1 className="mt-3 text-4xl sm:text-5xl lg:text-6xl font-semibold tracking-tight">
              {s.title}
            </h1>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mt-5 max-w-2xl text-white/85 text-lg">{s.short}</p>
          </Reveal>
        </div>
      </section>

      <section className="section">
        <div className="container-x grid md:grid-cols-12 gap-12">
          <div className="md:col-span-7">
            <Reveal>
              <p className="eyebrow">Overview</p>
              <p className="mt-4 text-lg text-[#0F172A] leading-relaxed">
                {s.long}
              </p>
            </Reveal>

            <Reveal delay={0.1}>
              <h3 className="mt-12 text-2xl font-semibold text-[#0F172A]">
                What's included
              </h3>
              <ul className="mt-6 space-y-3">
                {s.bullets.map((b) => (
                  <li
                    key={b}
                    data-testid={`service-bullet-${b.slice(0, 12)}`}
                    className="flex items-start gap-3 text-[#475569]"
                  >
                    <span className="mt-1 w-5 h-5 rounded-full bg-[#F1F5F2] text-[#1C3F3A] flex items-center justify-center flex-shrink-0">
                      <Check size={12} />
                    </span>
                    {b}
                  </li>
                ))}
              </ul>
            </Reveal>
          </div>

          <div className="md:col-span-5">
            <Reveal delay={0.05}>
              <div className="bg-[#F1F5F2] rounded-2xl p-8 border border-[#E2E8F0] sticky top-28">
                <p className="eyebrow">Engage with us</p>
                <h4 className="mt-3 text-2xl font-semibold text-[#0F172A]">
                  Start with a scoping call.
                </h4>
                <p className="mt-3 text-[#475569] text-sm leading-relaxed">
                  Tell us about the team, the challenge and the timeframe. We'll
                  outline a fit-for-purpose programme and a clear quote.
                </p>
                <Link
                  to="/contact"
                  data-testid="service-cta"
                  className="btn-primary mt-6 w-full justify-center"
                >
                  Request a consultation
                </Link>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      <section className="section bg-[#F1F5F2]">
        <div className="container-x">
          <Reveal>
            <p className="eyebrow">Continue exploring</p>
            <h3 className="mt-3 text-3xl font-semibold text-[#0F172A]">
              Other services
            </h3>
          </Reveal>
          <div className="mt-10 grid md:grid-cols-3 gap-6">
            {others.map((o, i) => (
              <Reveal key={o.slug} delay={i * 0.05}>
                <Link
                  to={`/services/${o.slug}`}
                  data-testid={`other-service-${o.slug}`}
                  className="block bg-white rounded-2xl p-6 hover:-translate-y-1 transition-transform"
                >
                  <span className="text-[10px] uppercase tracking-[0.2em] text-[#81B29A]">
                    {o.category}
                  </span>
                  <h4 className="mt-2 text-xl font-medium text-[#0F172A]">
                    {o.title}
                  </h4>
                  <p className="mt-3 text-sm text-[#475569] leading-relaxed">
                    {o.short}
                  </p>
                </Link>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <CTABanner />
      <div className="h-24" />
    </>
  );
}

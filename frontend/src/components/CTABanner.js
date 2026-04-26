import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import Reveal from "./Reveal";

export default function CTABanner({
  title = "Ready to build a measurably healthier workplace?",
  subtitle = "Book a 30-minute consultation. We'll listen, then map a path.",
  ctaLabel = "Book a consultation",
  ctaTo = "/contact",
}) {
  return (
    <section className="container-x">
      <Reveal>
        <div className="relative overflow-hidden rounded-3xl bg-[#1C3F3A] text-white p-10 md:p-16 grid md:grid-cols-12 gap-8 items-center">
          <div className="grain" />
          <div className="md:col-span-8 relative">
            <h3 className="text-3xl md:text-4xl font-semibold tracking-tight leading-tight">
              {title}
            </h3>
            <p className="mt-4 text-white/75 max-w-xl">{subtitle}</p>
          </div>
          <div className="md:col-span-4 relative md:flex md:justify-end">
            <Link
              to={ctaTo}
              data-testid="cta-banner-btn"
              className="inline-flex items-center gap-2 bg-[#D4A373] text-[#1C3F3A] px-6 py-3 rounded-full font-medium hover:bg-white transition-colors"
            >
              {ctaLabel}
              <ArrowUpRight size={18} />
            </Link>
          </div>
        </div>
      </Reveal>
    </section>
  );
}

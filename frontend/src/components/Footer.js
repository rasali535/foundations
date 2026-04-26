import { Link } from "react-router-dom";
import { Mail, Phone, MapPin } from "lucide-react";
import { NAV, SITE } from "../data/site";

export default function Footer() {
  return (
    <footer
      data-testid="site-footer"
      className="bg-[#1C3F3A] text-white/90 mt-24"
    >
      <div className="container-x py-20 grid md:grid-cols-12 gap-12">
        <div className="md:col-span-5">
          <div className="flex items-center gap-3 mb-6">
            <span className="w-10 h-10 rounded-full bg-[#D4A373] flex items-center justify-center text-[#1C3F3A] font-semibold">
              F
            </span>
            <div>
              <p className="font-medium">{SITE.name}</p>
              <p className="text-xs text-white/60 uppercase tracking-[0.2em]">
                {SITE.parent}
              </p>
            </div>
          </div>
          <p className="text-white/70 text-sm leading-relaxed max-w-md">
            We help organisations across Southern Africa build measurably
            healthier, safer and higher-performing workplaces.
          </p>
        </div>

        <div className="md:col-span-3">
          <p className="eyebrow mb-5" style={{ color: "#D4A373" }}>
            Navigate
          </p>
          <ul className="space-y-3 text-sm">
            {NAV.map((n) => (
              <li key={n.to}>
                <Link
                  to={n.to}
                  data-testid={`footer-nav-${n.label.toLowerCase()}`}
                  className="text-white/80 hover:text-white transition-colors"
                >
                  {n.label}
                </Link>
              </li>
            ))}
            <li>
              <Link
                to="/privacy"
                data-testid="footer-nav-privacy"
                className="text-white/80 hover:text-white transition-colors"
              >
                Privacy Policy
              </Link>
            </li>
          </ul>
        </div>

        <div className="md:col-span-4">
          <p className="eyebrow mb-5" style={{ color: "#D4A373" }}>
            Reach us
          </p>
          <ul className="space-y-4 text-sm text-white/85">
            <li className="flex items-start gap-3">
              <MapPin size={18} className="mt-0.5 text-[#D4A373]" />
              <span>{SITE.address}</span>
            </li>
            <li className="flex items-start gap-3">
              <Mail size={18} className="mt-0.5 text-[#D4A373]" />
              <a
                href={`mailto:${SITE.email}`}
                data-testid="footer-email"
                className="hover:text-white"
              >
                {SITE.email}
              </a>
            </li>
            <li className="flex items-start gap-3">
              <Phone size={18} className="mt-0.5 text-[#D4A373]" />
              <a
                href={`tel:${SITE.phone.replace(/\s+/g, "")}`}
                data-testid="footer-phone"
                className="hover:text-white"
              >
                {SITE.phone}
              </a>
            </li>
          </ul>
        </div>
      </div>
      <div className="border-t border-white/10">
        <div className="container-x py-6 flex flex-col md:flex-row items-center justify-between text-xs text-white/50 gap-2">
          <p>© {new Date().getFullYear()} {SITE.name}. All rights reserved.</p>
          <p>{SITE.hours}</p>
        </div>
      </div>
    </footer>
  );
}

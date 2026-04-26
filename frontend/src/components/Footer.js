import { Link } from "react-router-dom";
import { Mail, Phone, MapPin } from "lucide-react";
import { NAV, SITE } from "../data/site";

export default function Footer() {
  return (
    <footer
      data-testid="site-footer"
      className="bg-[#1C3F3A] text-white/90 mt-24"
    >
      {/* Brand + nav row */}
      <div className="container-x py-12 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-8 border-b border-white/10">
        <Link to="/" className="flex items-center gap-3">
          <span className="w-10 h-10 rounded-full bg-[#D4A373] flex items-center justify-center text-[#1C3F3A] font-semibold">
            F
          </span>
          <div>
            <p className="font-medium leading-none">{SITE.name}</p>
            <p className="text-[10px] mt-1 text-white/60 uppercase tracking-[0.2em]">
              {SITE.parent}
            </p>
          </div>
        </Link>

        <nav className="flex flex-wrap items-center gap-x-7 gap-y-3 text-sm">
          {NAV.map((n) => (
            <Link
              key={n.to}
              to={n.to}
              data-testid={`footer-nav-${n.label.toLowerCase()}`}
              className="text-white/80 hover:text-white transition-colors"
            >
              {n.label}
            </Link>
          ))}
          <Link
            to="/privacy"
            data-testid="footer-nav-privacy"
            className="text-white/80 hover:text-white transition-colors"
          >
            Privacy
          </Link>
        </nav>
      </div>

      {/* Contact row — centered */}
      <div className="container-x py-8 flex flex-col items-center justify-center gap-4 text-sm text-white/85 text-center">
        <div className="flex flex-wrap items-center justify-center gap-x-8 gap-y-3">
          <span className="flex items-center gap-2">
            <MapPin size={16} className="text-[#D4A373]" />
            {SITE.address}
          </span>
          <a
            href={`mailto:${SITE.email}`}
            data-testid="footer-email"
            className="flex items-center gap-2 hover:text-white"
          >
            <Mail size={16} className="text-[#D4A373]" />
            {SITE.email}
          </a>
          <a
            href={`tel:${SITE.phone.replace(/\s+/g, "")}`}
            data-testid="footer-phone"
            className="flex items-center gap-2 hover:text-white"
          >
            <Phone size={16} className="text-[#D4A373]" />
            {SITE.phone}
          </a>
        </div>
        <p className="text-xs text-white/60">{SITE.hours}</p>
      </div>

      {/* Copyright — centered */}
      <div className="border-t border-white/10">
        <div className="container-x py-5 flex flex-col sm:flex-row items-center justify-center gap-2 sm:gap-4 text-xs text-white/50 text-center">
          <span>
            © {new Date().getFullYear()} {SITE.name}. All rights reserved.
          </span>
          <span className="hidden sm:inline text-white/30">·</span>
          <span data-testid="footer-credit">
            Web dev by{" "}
            <a
              href="https://www.rasalibassist.themaplin.com"
              target="_blank"
              rel="noopener noreferrer"
              data-testid="footer-credit-link"
              className="text-[#D4A373] font-medium hover:text-white transition-colors"
            >
              Ras Ali Labs
            </a>
          </span>
        </div>
      </div>
    </footer>
  );
}

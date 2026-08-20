import { Link } from "react-router-dom";
import { Mail, Phone, MapPin, MessageCircle } from "lucide-react";
import { SITE, WHATSAPP_LINK, getWhatsAppUrl } from "../data/site";

export default function Footer() {
  return (
    <footer
      data-testid="site-footer"
      className="bg-[#1C3F3A] text-white/90 mt-24 border-t border-[#15302C]"
    >
      <div className="container-x py-16 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-10">
        {/* Brand column */}
        <div className="lg:col-span-2 space-y-4">
          <Link to="/" className="flex items-center gap-3">
            <img
              src={SITE.logo}
              alt={SITE.name}
              className="h-16 w-auto object-contain"
            />
            <div>
              <p className="font-semibold text-lg leading-tight text-white">{SITE.name}</p>
              <p className="text-[10px] mt-0.5 text-white/60 uppercase tracking-[0.2em]">
                {SITE.parent}
              </p>
            </div>
          </Link>
          <p className="text-sm text-white/70 max-w-sm leading-relaxed">
            {SITE.tagline}
          </p>
          <p className="text-xs text-white/50 leading-relaxed max-w-sm">
            Evidence-led counselling, workplace wellbeing, corporate training, and digital masterclasses based in Gaborone, Botswana.
          </p>
          <div className="pt-2 flex items-center gap-3">
            <a
              href={getWhatsAppUrl("general")}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#81B29A] text-[#1C3F3A] text-xs font-semibold hover:bg-white transition-colors"
            >
              <MessageCircle size={14} />
              <span>WhatsApp FCA</span>
            </a>
          </div>
        </div>

        {/* Pathway 1 & 2 */}
        <div className="space-y-3 text-sm">
          <p className="text-xs uppercase tracking-[0.15em] text-[#D4A373] font-semibold">Services</p>
          <ul className="space-y-2 text-white/80">
            <li>
              <Link to="/counselling" className="hover:text-white transition-colors">
                Personal Counselling
              </Link>
            </li>
            <li>
              <Link to="/counselling" className="hover:text-white transition-colors">
                Couples & Family
              </Link>
            </li>
            <li>
              <Link to="/corporate-wellness" className="hover:text-white transition-colors">
                Workplace EAP
              </Link>
            </li>
            <li>
              <Link to="/corporate-wellness" className="hover:text-white transition-colors">
                ISO 45003 Risk Management
              </Link>
            </li>
            <li>
              <Link to="/training-team-building" className="hover:text-white transition-colors">
                Team Building & Retreats
              </Link>
            </li>
          </ul>
        </div>

        {/* Pathway 3 & 4 */}
        <div className="space-y-3 text-sm">
          <p className="text-xs uppercase tracking-[0.15em] text-[#D4A373] font-semibold">Learning & Hub</p>
          <ul className="space-y-2 text-white/80">
            <li>
              <Link to="/learning" className="hover:text-white transition-colors">
                Online Programmes
              </Link>
            </li>
            <li>
              <Link to="/resources" className="hover:text-white transition-colors">
                7-Day Steadiness Planner
              </Link>
            </li>
            <li>
              <Link to="/about" className="hover:text-white transition-colors">
                About FCA
              </Link>
            </li>
            <li>
              <Link to="/contact" className="hover:text-white transition-colors">
                Contact & Bookings
              </Link>
            </li>
            <li>
              <Link to="/intake" className="hover:text-white transition-colors">
                Confidential Intake Portal
              </Link>
            </li>
          </ul>
        </div>

        {/* Contact info */}
        <div className="space-y-3 text-sm">
          <p className="text-xs uppercase tracking-[0.15em] text-[#D4A373] font-semibold">Gaborone Office</p>
          <p className="text-xs text-white/70 flex items-start gap-2">
            <MapPin size={15} className="text-[#D4A373] flex-shrink-0 mt-0.5" />
            <span>{SITE.address}</span>
          </p>
          <p className="text-xs text-white/70 flex items-center gap-2">
            <Mail size={15} className="text-[#D4A373] flex-shrink-0" />
            <a href={`mailto:${SITE.email}`} className="hover:text-white transition-colors">
              {SITE.email}
            </a>
          </p>
          <p className="text-xs text-white/70 flex items-center gap-2">
            <Phone size={15} className="text-[#D4A373] flex-shrink-0" />
            <a href={`tel:${SITE.phone.replace(/\s+/g, "")}`} className="hover:text-white transition-colors">
              {SITE.phone}
            </a>
          </p>
          <p className="text-[11px] text-white/50 pt-1">
            {SITE.hours}
          </p>
        </div>
      </div>

      {/* Emergency Notice */}
      <div className="bg-[#15302C] py-4 border-t border-white/5">
        <div className="container-x text-center text-xs text-white/60">
          <strong className="text-white/80">Emergency Advisory:</strong> Foundations Counselling Academy provides structured outpatient counselling and workplace support and is not an immediate emergency rescue service. If you or someone you know is in immediate crisis, please contact Botswana Emergency Services by dialing <strong className="text-white">999</strong> or your nearest healthcare facility.
        </div>
      </div>

      {/* Bottom Legal & Copyright Bar */}
      <div className="border-t border-white/10 bg-[#122824]">
        <div className="container-x py-6 flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-white/50">
          <div className="flex flex-wrap items-center justify-center gap-4 text-white/60">
            <Link to="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link>
            <span>·</span>
            <Link to="/terms" className="hover:text-white transition-colors">Terms of Service</Link>
            <span>·</span>
            <Link to="/cookies" className="hover:text-white transition-colors">Cookie Notice</Link>
            <span>·</span>
            <Link to="/disclaimer" className="hover:text-white transition-colors">Clinical Disclaimer</Link>
            <span>·</span>
            <Link to="/refunds" className="hover:text-white transition-colors">Refund Policy</Link>
          </div>
          <div className="text-center md:text-right">
            <span>© {new Date().getFullYear()} {SITE.name}. All rights reserved.</span>
          </div>
        </div>
      </div>
    </footer>
  );
}

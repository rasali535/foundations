import { MessageCircle } from "lucide-react";
import { getWhatsAppUrl } from "../data/site";

export default function FloatingWhatsApp() {
  return (
    <a
      href={getWhatsAppUrl("general")}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Chat on WhatsApp with FCA"
      data-testid="floating-whatsapp-btn"
      className="fixed bottom-6 left-6 z-40 flex items-center gap-2.5 px-4 py-3 bg-[#25D366] text-white rounded-full shadow-lg hover:shadow-xl hover:bg-[#20bd5a] transition-all hover:scale-105 group sm:px-4"
    >
      <MessageCircle size={22} className="fill-white/20" />
      <span className="text-sm font-semibold tracking-wide hidden sm:inline">
        WhatsApp FCA
      </span>
    </a>
  );
}

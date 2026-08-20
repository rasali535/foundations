import { useEffect, useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { Menu, X, ArrowUpRight } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { NAV, SITE } from "../data/site";

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      data-testid="site-header"
      className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${
        scrolled
          ? "backdrop-blur-xl bg-white/90 border-b border-slate-200/80 shadow-sm"
          : "bg-transparent"
      }`}
    >
      <div className="container-x flex items-center justify-between h-20">
        <Link
          to="/"
          data-testid="nav-logo"
          className="flex items-center gap-3 group"
        >
          <img
            src={SITE.logo}
            alt={SITE.name}
            className="h-14 w-auto object-contain"
          />
          <span className="hidden sm:block text-[10px] tracking-[0.2em] uppercase text-[#475569] leading-tight">
            A Pameltex Group<br />company
          </span>
        </Link>

        <div className="hidden lg:flex items-center gap-7">
          <nav className="flex items-center gap-6" aria-label="Main Navigation">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, "-")}`}
                end={item.to === "/"}
                className={({ isActive }) =>
                  `text-sm font-medium transition-colors relative py-1 ${
                    isActive
                      ? "text-[#1C3F3A] font-semibold"
                      : "text-[#475569] hover:text-[#1C3F3A]"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    {item.label}
                    {isActive && (
                      <motion.span
                        layoutId="navdot"
                        className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full bg-[#D4A373]"
                      />
                    )}
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          <Link
            to="/contact"
            data-testid="nav-cta"
            className="btn-primary text-sm shadow-sm hover:shadow-md transition-all flex items-center gap-1.5"
          >
            <span>Book / Enquire</span>
            <ArrowUpRight size={15} />
          </Link>
        </div>

        <button
          data-testid="mobile-menu-toggle"
          aria-label="Toggle menu"
          onClick={() => setOpen(!open)}
          className="lg:hidden p-2 rounded-full hover:bg-black/5 text-[#1C3F3A]"
        >
          {open ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="lg:hidden overflow-hidden bg-white border-t border-slate-100 shadow-xl"
          >
            <div className="container-x py-6 flex flex-col gap-4">
              {NAV.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  data-testid={`mobile-nav-${item.label.toLowerCase().replace(/\s+/g, "-")}`}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    `text-base font-medium py-2 border-b border-slate-50 transition-colors ${
                      isActive ? "text-[#1C3F3A] font-semibold" : "text-[#475569]"
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
              <Link
                to="/contact"
                onClick={() => setOpen(false)}
                data-testid="mobile-nav-cta"
                className="btn-primary text-center mt-2 flex items-center justify-center gap-2"
              >
                Book / Enquire
                <ArrowUpRight size={16} />
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}

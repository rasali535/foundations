import { useEffect, useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { Menu, X } from "lucide-react";
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
          ? "backdrop-blur-xl bg-white/80 border-b border-white/40"
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
            className="h-14 w-14 object-contain rounded-lg p-1"
          />
          <span className="hidden sm:block text-[10px] tracking-[0.2em] uppercase text-[#475569] leading-tight">
            A Pameltex Group<br />company
          </span>
        </Link>

        <div className="hidden lg:flex items-center gap-8">
          <nav className="flex items-center gap-6">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                data-testid={`nav-${item.label.toLowerCase()}`}
                end={item.to === "/"}
                className={({ isActive }) =>
                  `text-sm font-medium transition-colors relative ${
                    isActive
                      ? "text-[#1C3F3A]"
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
                        className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full bg-[#D4A373]"
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
            className="btn-primary text-sm"
          >
            Book a consultation
          </Link>
        </div>

        <button
          data-testid="mobile-menu-toggle"
          aria-label="Toggle menu"
          onClick={() => setOpen(!open)}
          className="lg:hidden p-2 rounded-full hover:bg-black/5"
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="lg:hidden overflow-hidden bg-white border-t border-slate-100"
          >
            <div className="container-x py-6 flex flex-col gap-4">
              {NAV.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  data-testid={`mobile-nav-${item.label.toLowerCase()}`}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    `text-base font-medium ${
                      isActive ? "text-[#1C3F3A]" : "text-[#475569]"
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
                className="btn-primary text-sm w-fit mt-2"
              >
                Book a consultation
              </Link>
              <p className="text-xs text-[#475569] mt-4">{SITE.parent}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}

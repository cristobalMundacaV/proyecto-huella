import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { Outlet, useLocation } from "react-router-dom";

import Navbar from "./Navbar";
import Sidebar from "./Sidebar";
import { useAuth } from "@/features/auth/context/AuthContext";
import { IconButton } from "@/shared/ui/Button";

export default function AuthenticatedLayout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { pathname } = useLocation();
  const { user } = useAuth();

  useEffect(() => { setMobileMenuOpen(false); }, [pathname]);

  useEffect(() => {
    if (!mobileMenuOpen) return undefined;
    const previousOverflow = document.body.style.overflow;
    const closeOnEscape = (event) => {
      if (event.key === "Escape") setMobileMenuOpen(false);
    };
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [mobileMenuOpen]);

  useEffect(() => {
    if (!pathname.startsWith("/obras/")) window.scrollTo({ top: 0, behavior: "auto" });
  }, [pathname]);

  return (
    <main className="min-h-screen bg-[var(--bg-main)] text-[var(--text-main)]">

      <div>
        <Navbar
          onOpenMobileMenu={() => setMobileMenuOpen(true)}
        />

        {user?.is_demo && (
          <div className="border-b border-[var(--status-warning)]/25 bg-[var(--warning-bg)] px-4 py-2 text-center text-xs font-bold uppercase tracking-wide text-[var(--status-warning)]">
            Modo demo: solo lectura
          </div>
        )}

        <div className="flex min-h-[calc(100vh-72px)] flex-col lg:flex-row">
          <div className="hidden lg:block">
            <Sidebar />
          </div>

          <AnimatePresence>
            {mobileMenuOpen && (
              <motion.div
                className="fixed inset-0 z-50 lg:hidden"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <button
                  type="button"
                  className="absolute inset-0 bg-slate-950/30 backdrop-blur-sm"
                  onClick={() => setMobileMenuOpen(false)}
                  aria-label="Cerrar menú"
                />

                <motion.div
                  className="absolute left-0 top-0 h-full w-[85vw] max-w-sm overflow-y-auto border-r border-white/10 bg-[var(--sidebar)] shadow-2xl"
                  initial={{ x: "-100%" }}
                  animate={{ x: 0 }}
                  exit={{ x: "-100%" }}
                >
                  <IconButton
                    aria-label="Cerrar menú"
                    icon={X}
                    onClick={() => setMobileMenuOpen(false)}
                    className="absolute right-4 top-4"
                  />

                  <Sidebar
                    onNavigate={() => setMobileMenuOpen(false)}
                  />
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>

          <section className="min-w-0 flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-10 lg:py-10">
            <Outlet />
          </section>
        </div>
      </div>
    </main>
  );
}
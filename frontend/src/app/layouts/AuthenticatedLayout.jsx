import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { Outlet, useLocation } from "react-router-dom";

import Navbar from "./Navbar";
import Sidebar from "./Sidebar";
import Breadcrumbs from "@/shared/components/Breadcrumbs";
import { useAuth } from "@/features/auth/context/AuthContext";
import { IconButton } from "@/shared/ui/Button";

export default function AuthenticatedLayout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [companyStatus, setCompanyStatus] = useState(null);
  const { pathname } = useLocation();
  const { user } = useAuth();

  useEffect(() => { setMobileMenuOpen(false); }, [pathname]);
  useEffect(() => {
    if (!pathname.startsWith("/obras/")) window.scrollTo({ top: 0, behavior: "auto" });
  }, [pathname]);

  return <main className="min-h-screen bg-[var(--bg-main)] text-[var(--text-main)]">
    <Navbar onOpenMobileMenu={() => setMobileMenuOpen(true)} />
    {user?.is_demo && <div className="fixed left-1/2 top-4 z-50 -translate-x-1/2 rounded-full border border-amber-300/30 bg-amber-300/10 px-4 py-2 text-xs font-bold uppercase tracking-wide text-amber-100 shadow-xl backdrop-blur">Modo demo: solo lectura</div>}
    <div className="flex min-h-[calc(100vh-72px)] flex-col lg:flex-row">
      <div className="hidden lg:block"><Sidebar systemStatus={companyStatus} /></div>
      <AnimatePresence>{mobileMenuOpen && <motion.div className="fixed inset-0 z-50 lg:hidden" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
        <button type="button" className="absolute inset-0 bg-slate-950/30 backdrop-blur-sm" onClick={() => setMobileMenuOpen(false)} aria-label="Cerrar menú" />
        <motion.div className="absolute left-0 top-0 h-full w-[85vw] max-w-sm overflow-y-auto border-r border-white/10 bg-[var(--sidebar)] shadow-2xl" initial={{ x: "-100%" }} animate={{ x: 0 }} exit={{ x: "-100%" }}>
          <IconButton aria-label="Cerrar menú" icon={X} onClick={() => setMobileMenuOpen(false)} className="absolute right-4 top-4" />
          <Sidebar onNavigate={() => setMobileMenuOpen(false)} systemStatus={companyStatus} />
        </motion.div>
      </motion.div>}</AnimatePresence>
      <section className="min-w-0 flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-10 lg:py-10">
        <Breadcrumbs />
        <Outlet context={{ setCompanyStatus }} />
      </section>
    </div>
  </main>;
}

import { ChevronDown, Leaf, LogOut, Menu, UserRound } from "lucide-react";
import { useState } from "react";

import { useAuth } from "@/features/auth/context/AuthContext";

function Navbar({ onOpenMobileMenu, onSetActiveView }) {
    const { logout, user } = useAuth();
    const [open, setOpen] = useState(false);

    const displayName =
        user?.first_name ||
        user?.nombre ||
        user?.username ||
        "Usuario";

    return (
        <header className="sticky top-0 z-40 border-b border-emerald-100/80 bg-white/88 px-4 py-3 shadow-[0_14px_42px_rgba(15,23,42,0.06)] backdrop-blur-xl sm:px-6 lg:px-10">
            <div className="mx-auto flex max-w-none items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                    <button
                        type="button"
                        onClick={onOpenMobileMenu}
                        className="flex h-11 w-11 items-center justify-center rounded-2xl border border-emerald-100 bg-white text-slate-700 shadow-sm transition hover:border-emerald-200 hover:bg-emerald-50 lg:hidden"
                        aria-label="Abrir menú"
                    >
                        <Menu size={20} />
                    </button>

                    <button
                        type="button"
                        onClick={() => onSetActiveView?.("dashboard")}
                        className="flex items-center gap-3"
                    >
                        <div className="rounded-2xl border border-emerald-200 bg-[linear-gradient(180deg,#123D34,#0F2D27)] p-2.5 text-emerald-200 shadow-[0_14px_30px_rgba(15,45,39,0.22)]">
                            <Leaf size={22} />
                        </div>
                        <div className="hidden text-left sm:block">
                            <p className="text-lg font-black tracking-tight text-slate-950">
                                Carbono Zero
                            </p>
                            <p className="text-xs font-semibold text-slate-500">
                                Inteligencia ambiental por rubro
                            </p>
                        </div>
                    </button>
                </div>

                <div className="relative">
                    <button
                        type="button"
                        onClick={() => setOpen((current) => !current)}
                        className="inline-flex items-center gap-3 rounded-2xl border border-emerald-100 bg-emerald-50/80 px-3 py-2 text-sm font-bold text-emerald-900 transition hover:border-emerald-200 hover:bg-emerald-100"
                    >
                        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-white text-emerald-700 shadow-sm">
                            <UserRound size={18} />
                        </span>
                        <span className="hidden sm:inline">{displayName}</span>
                        <ChevronDown size={16} />
                    </button>

                    {open && (
                        <div className="absolute right-0 mt-3 w-72 overflow-hidden rounded-3xl border border-emerald-100 bg-white shadow-[0_24px_70px_rgba(15,23,42,0.16)]">
                            <div className="border-b border-slate-100 p-4">
                                <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">
                                    Mi cuenta
                                </p>
                                <p className="mt-1 text-sm font-black text-slate-950">{displayName}</p>
                                <p className="text-xs font-semibold text-slate-500">
                                    {user?.email || "Sin correo registrado"}
                                </p>
                            </div>

                            <button
                                type="button"
                                onClick={() => {
                                    setOpen(false);
                                    onSetActiveView?.("usuarios");
                                }}
                                className="flex w-full items-center gap-3 px-4 py-3 text-left text-sm font-bold text-slate-700 transition hover:bg-emerald-50"
                            >
                                <UserRound size={17} />
                                Ver información de usuario
                            </button>

                            <button
                                type="button"
                                onClick={logout}
                                className="flex w-full items-center gap-3 px-4 py-3 text-left text-sm font-bold text-rose-700 transition hover:bg-rose-50"
                            >
                                <LogOut size={17} />
                                Cerrar sesión
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </header>
    );
}

export default Navbar;

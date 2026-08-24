import {
  ChevronDown,
  LogOut,
  Menu,
  ShieldCheck,
  KeyRound,
  UserRound,
} from "lucide-react";

import { useState } from "react";
import {
  Link,
  useLocation,
  useNavigate,
} from "react-router-dom";

import { getPageContext } from "@/app/navigation";
import { useAuth } from "@/features/auth/context/AuthContext";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { getActivePreset } from "@/presets/registry";
import { IconButton } from "@/shared/ui/Button";
import WorkspaceSelector from "@/features/workspace/components/WorkspaceSelector";
import { useOperationalWorkspace } from "@/features/workspace/context/OperationalWorkspaceContext";

export default function Navbar({
  onOpenMobileMenu,
}) {
  const { logout, user } = useAuth();

  const {
    activeOrganizacion,
  } = useOrganizacionActiva();

  const { pathname } = useLocation();
  const navigate = useNavigate();

  const [open, setOpen] = useState(false);
  const { workspaces } = useOperationalWorkspace();

  const displayName =
    user?.first_name ||
    user?.nombre ||
    user?.username ||
    "Usuario";

  const preset = getActivePreset(
    activeOrganizacion?.preset ||
    "construccion"
  );

  const pageContext = getPageContext(
    pathname,
    preset
  );

  const handleLogout = async () => {
    await logout();

    navigate("/login", {
      replace: true,
    });
  };

  return (
    <header className="sticky top-0 z-40 border-b border-[var(--border-subtle)] bg-[var(--bg-elevated)]/95 px-[var(--page-padding)] py-3 shadow-[var(--shadow-sm)] backdrop-blur-xl">
      <div className="flex items-center gap-5">
        <div className="flex shrink-0 items-center gap-3">
          <IconButton
            aria-label="Abrir menú"
            icon={Menu}
            onClick={onOpenMobileMenu}
            className="lg:hidden"
          />

          <Link
            to="/inicio"
            className="flex items-center gap-3 rounded-[var(--radius-md)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
          >
            <img
              src="/brand/carbono-zero-logo.png"
              alt="Carbono Zero"
              className="h-10 w-auto object-contain sm:h-11"
            />
          </Link>
        </div>

        <div
          aria-hidden="true"
          className="hidden h-9 w-px bg-[var(--border-default)] md:block"
        />

        <div className="hidden min-w-0 flex-1 md:block">
          <p className="truncate text-[15px] font-black leading-tight text-[var(--text-primary)]">
            {pageContext.title}
          </p>

          <p className="mt-1 truncate text-xs text-[var(--text-muted)]">
            {pageContext.description}
          </p>
        </div>

        {workspaces.length > 1 && <WorkspaceSelector compact />}
        <div className="relative ml-auto">
          <button
            type="button"
            onClick={() =>
              setOpen(current => !current)
            }
            className="inline-flex items-center gap-3 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2 text-sm font-bold shadow-sm transition hover:border-emerald-700/20 hover:bg-emerald-50/50 focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
          >
            <UserRound
              aria-hidden="true"
              size={18}
            />

            <span className="hidden sm:inline">
              {displayName}
            </span>

            <ChevronDown
              aria-hidden="true"
              size={16}
              className={`transition-transform duration-200 ${open
                ? "rotate-180"
                : ""
                }`}
            />
          </button>

          {open && (
            <div className="absolute right-0 mt-3 w-72 overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-elevated)] shadow-[var(--shadow-lg)]">
              <div className="border-b border-[var(--border-subtle)] p-4">
                <p className="font-black text-[var(--text-primary)]">
                  {displayName}
                </p>

                <p className="mt-1 truncate text-xs text-[var(--text-muted)]">
                  {user?.email ||
                    "Sin correo registrado"}
                </p>
              </div>

              <Link
                to="/administracion/equipo"
                onClick={() =>
                  setOpen(false)
                }
                className="flex items-center gap-3 px-4 py-3 text-sm font-bold text-[var(--text-primary)] transition hover:bg-[var(--bg-subtle)]"
              >
                <UserRound
                  aria-hidden="true"
                  size={17}
                />

                Ver información de usuario
              </Link>
              <Link
                to="/perfil/seguridad"
                onClick={() => setOpen(false)}
                className="flex items-center gap-3 px-4 py-3 text-sm font-bold text-[var(--text-primary)] transition hover:bg-[var(--bg-subtle)]"
              >
                <KeyRound aria-hidden="true" size={17} />
                Seguridad y contraseña
              </Link>
              {user?.is_superuser && <Link to="/saas" onClick={() => setOpen(false)} className="flex items-center gap-3 px-4 py-3 text-sm font-bold text-emerald-800 transition hover:bg-emerald-50"><ShieldCheck aria-hidden="true" size={17} />Abrir Carbono Zero Global</Link>}

              <button
                type="button"
                onClick={handleLogout}
                className="flex w-full items-center gap-3 px-4 py-3 text-left text-sm font-bold text-[var(--status-danger)] transition hover:bg-[var(--danger-bg)]"
              >
                <LogOut
                  aria-hidden="true"
                  size={17}
                />

                Cerrar sesión
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="mt-2 md:hidden">
        <p className="truncate text-sm font-black text-[var(--text-primary)]">
          {pageContext.title}
        </p>

        <p className="mt-0.5 truncate text-[11px] text-[var(--text-muted)]">
          {pageContext.description}
        </p>
      </div>
    </header>
  );
}

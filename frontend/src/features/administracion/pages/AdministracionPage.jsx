import { Link } from "react-router-dom";

import {
  ArrowRight,
  Building2,
  ClipboardCheck,
  Factory,
  Settings2,
  ShieldCheck,
  UsersRound,
} from "lucide-react";

import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";


const primaryAreas = [
  {
    to: "/administracion/organizacion",
    title: "Organización",
    description:
      "Gestiona la identidad, el perfil de operación y el contexto de la organización activa.",
    icon: Building2,
    eyebrow: "Identidad",
    tone: "emerald",
  },

  {
    to: "/administracion/usuarios",
    title: "Usuarios y roles",
    description:
      "Controla quién tiene acceso a la organización y qué rol posee cada usuario.",
    icon: UsersRound,
    eyebrow: "Acceso",
    tone: "sky",
  },

  {
    to: "/administracion/configuracion",
    title: "Preferencias",
    description:
      "Configura opciones operativas para importaciones, documentos y reportes.",
    icon: Settings2,
    eyebrow: "Funcionamiento",
    tone: "amber",
  },
];


const secondaryAreas = [
  {
    to: "/administracion/estructura",
    title: "Estructura",
    description:
      "Revisa cómo está organizada la operación y sus unidades asociadas.",
    icon: Factory,
  },

  {
    to: "/administracion/diagnostico",
    title: "Diagnóstico",
    description:
      "Define contexto, aplicabilidad e información pendiente de completar.",
    icon: ClipboardCheck,
  },
];


export default function AdministracionPage() {
  const {
    activeOrganizacion,
  } = useOrganizacionActiva();


  return (
    <main className="space-y-6">

      <section className="overflow-hidden rounded-[28px] border border-emerald-700/20 bg-[linear-gradient(135deg,rgba(6,78,59,0.97)_0%,rgba(6,95,70,0.93)_48%,rgba(15,118,110,0.84)_100%)] p-6 text-white shadow-[0_18px_45px_rgba(6,78,59,0.16)]">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-100">
              Configuración · Organización
            </p>

            <h1 className="mt-2 text-3xl font-black">
              Administración
            </h1>

            <p className="mt-2 max-w-2xl text-sm leading-6 text-emerald-50/85">
              Gestiona la identidad de tu
              organización, sus usuarios,
              preferencias y estructura
              operativa desde un único lugar.
            </p>

            {activeOrganizacion
              ?.nombre && (
                <div className="mt-4">
                  <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold">
                    Organización activa ·{" "}
                    {
                      activeOrganizacion.nombre
                    }
                  </span>
                </div>
              )}
          </div>

          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border border-white/20 bg-white/10 text-white">
            <Settings2
              aria-hidden="true"
              size={28}
            />
          </div>
        </div>
      </section>


      <section
        className="space-y-4"
        aria-label="Administración principal"
      >
        <div>
          <p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">
            Administración principal
          </p>

          <h2 className="mt-1 text-2xl font-black text-[var(--text-primary)]">
            ¿Qué quieres administrar?
          </h2>

          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Las áreas principales controlan
            identidad, acceso y preferencias
            operativas.
          </p>
        </div>


        <div className="grid gap-4 lg:grid-cols-3">
          {primaryAreas.map(
            (area) => (
              <AreaCard
                key={area.to}
                area={area}
                prominent
              />
            )
          )}
        </div>
      </section>


      <section className="space-y-4">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">
            Contexto operativo
          </p>

          <h2 className="mt-1 text-xl font-black">
            Organización de la operación
          </h2>

          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Configura cómo se estructura la
            operación y qué información
            ambiental es aplicable.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {secondaryAreas.map(
            (area) => (
              <SecondaryAreaCard
                key={area.to}
                area={area}
              />
            )
          )}
        </div>
      </section>


      <aside className="overflow-hidden rounded-[22px] border border-emerald-100 bg-[linear-gradient(135deg,rgba(236,253,245,0.95),rgba(255,255,255,0.98))] p-5 shadow-[0_10px_30px_rgba(15,23,42,0.04)]">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700">
            <ShieldCheck
              aria-hidden="true"
              size={20}
            />
          </div>

          <div className="min-w-0 flex-1">
            <p className="font-black text-[var(--text-primary)]">
              Factores y metodologías
            </p>

            <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
              La administración cotidiana no
              modifica reglas científicas ni
              metodologías gobernadas. Esa
              información se gestiona desde
              Gobernanza.
            </p>
          </div>

          <Link
            className="inline-flex shrink-0 items-center gap-2 text-sm font-bold text-[var(--brand-primary)]"
            to="/gobernanza/factores"
          >
            Ir a Gobernanza

            <ArrowRight
              aria-hidden="true"
              size={16}
            />
          </Link>
        </div>
      </aside>
    </main>
  );
}


function AreaCard({
  area,
}) {
  const Icon =
    area.icon;


  const toneClass =
    area.tone === "sky"
      ? "bg-sky-50 text-sky-700"
      : area.tone === "amber"
        ? "bg-amber-50 text-amber-700"
        : "bg-emerald-50 text-emerald-700";


  return (
    <Link
      to={area.to}
      className="group rounded-[22px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
    >
      <article className="h-full min-h-[210px] rounded-[22px] border border-slate-200 bg-white p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)] transition group-hover:-translate-y-0.5 group-hover:border-emerald-200 group-hover:shadow-[0_18px_38px_rgba(15,23,42,0.08)]">
        <div className="flex items-start justify-between gap-3">
          <div
            className={`flex h-12 w-12 items-center justify-center rounded-2xl ${toneClass}`}
          >
            <Icon
              aria-hidden="true"
              size={22}
            />
          </div>

          <div className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 text-emerald-700 transition group-hover:border-emerald-200 group-hover:bg-emerald-50">
            <ArrowRight
              aria-hidden="true"
              size={17}
            />
          </div>
        </div>

        <p className="mt-5 text-xs font-black uppercase tracking-[0.12em] text-[var(--text-muted)]">
          {area.eyebrow}
        </p>

        <h2 className="mt-1 text-xl font-black text-[var(--text-primary)]">
          {area.title}
        </h2>

        <p className="mt-3 text-sm leading-6 text-[var(--text-muted)]">
          {area.description}
        </p>
      </article>
    </Link>
  );
}


function SecondaryAreaCard({
  area,
}) {
  const Icon =
    area.icon;


  return (
    <Link
      to={area.to}
      className="group rounded-[20px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
    >
      <article className="flex h-full items-start gap-4 rounded-[20px] border border-slate-200 bg-white p-5 shadow-[0_8px_24px_rgba(15,23,42,0.04)] transition group-hover:border-emerald-200">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700">
          <Icon
            aria-hidden="true"
            size={20}
          />
        </div>

        <div className="min-w-0 flex-1">
          <h3 className="font-black text-[var(--text-primary)]">
            {area.title}
          </h3>

          <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
            {area.description}
          </p>
        </div>

        <ArrowRight
          aria-hidden="true"
          size={17}
          className="mt-1 shrink-0 text-emerald-700"
        />
      </article>
    </Link>
  );
}
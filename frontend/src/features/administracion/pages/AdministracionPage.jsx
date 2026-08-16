import { Link } from "react-router-dom";
import { Building2, ClipboardCheck, Factory, Settings2, UsersRound } from "lucide-react";

import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { Card, CardContent, PageHeader } from "@/shared/ui";

const primaryAreas = [
  {
    to: "/administracion/organizacion",
    title: "Organización",
    description: "Identidad, perfil de operación y organización activa.",
    icon: Building2,
  },
  {
    to: "/administracion/usuarios",
    title: "Usuarios y roles",
    description: "Quién tiene acceso y qué rol tiene en la organización.",
    icon: UsersRound,
  },
  {
    to: "/administracion/configuracion",
    title: "Preferencias",
    description: "Opciones de funcionamiento para importación, documentos y reportes.",
    icon: Settings2,
  },
];

const secondaryAreas = [
  {
    to: "/administracion/estructura",
    title: "Estructura",
    description: "Cómo se organiza la operación de la organización activa.",
    icon: Factory,
  },
  {
    to: "/administracion/diagnostico",
    title: "Diagnóstico",
    description: "Contexto, aplicabilidad e información pendiente de completar.",
    icon: ClipboardCheck,
  },
];

export default function AdministracionPage() {
  const { activeOrganizacion } = useOrganizacionActiva();

  return (
    <main className="space-y-7">
      <PageHeader
        eyebrow="Configuración"
        title="Administración"
        description="Gestiona la organización, sus usuarios y las preferencias de funcionamiento."
        metadata={activeOrganizacion?.nombre || undefined}
      />

      <section className="grid gap-4 lg:grid-cols-3" aria-label="Administración principal">
        {primaryAreas.map((area) => <AreaCard key={area.to} area={area} prominent />)}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-black">Organización de la operación</h2>
        <div className="grid gap-3 md:grid-cols-2">
          {secondaryAreas.map((area) => <AreaCard key={area.to} area={area} />)}
        </div>
      </section>

      <aside className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-subtle)] p-4 text-sm text-[var(--text-muted)]">
        Factores y metodologías se gestionan desde <Link className="font-bold text-[var(--brand-primary)]" to="/gobernanza/factores">Gobernanza</Link>.
      </aside>
    </main>
  );
}

function AreaCard({ area, prominent = false }) {
  const Icon = area.icon;
  return (
    <Link
      to={area.to}
      className="block rounded-[var(--radius-lg)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
    >
      <Card className="h-full transition hover:border-[var(--brand-primary)]">
        <CardContent className={prominent ? "min-h-40" : "min-h-32"}>
          <Icon size={20} className="text-[var(--brand-primary)]" aria-hidden="true" />
          <h2 className="mt-4 text-lg font-black">{area.title}</h2>
          <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">{area.description}</p>
        </CardContent>
      </Card>
    </Link>
  );
}

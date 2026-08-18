import { useMemo } from "react";
import {
  ArrowRight,
  Bot,
  CheckCircle2,
  ChevronRight,
  Lightbulb,
  Sparkles,
  Target,
  TriangleAlert,
} from "lucide-react";
import { Link } from "react-router-dom";

import {
  Button,
  EmptyState,
  StatusBadge,
} from "@/shared/ui";

const attentionSignals = [
  {
    id: "signal-1",
    title: "Reducir distancia logística en 10%",
    priority: "media",
    summary:
      "Reducir kilómetros recorridos disminuye emisiones de transporte de forma proporcional y mejora la eficiencia operativa.",
    area: "Transporte",
    nextStep:
      "Comparar alternativa técnica y costo operacional para implementar el ajuste.",
    details: [
      "Se detectó oportunidad en recorridos repetidos dentro de la obra.",
      "Existe espacio para consolidar viajes y revisar rutas actuales.",
      "La señal todavía requiere validación operativa antes de transformarse en acción.",
    ],
    actionLabel: "Revisar problemas",
    actionTo: "/problemas",
  },
  {
    id: "signal-2",
    title: "Reducir factor de Acero estructural en 10%",
    priority: "media",
    summary:
      "Basado en emisiones reales del componente Acero estructural, existe una oportunidad concreta de reducción.",
    area: "Materiales",
    nextStep:
      "Comparar alternativa técnica y costo operacional para definir factibilidad.",
    details: [
      "La señal surge del peso relativo del acero dentro del impacto total.",
      "Podría abordarse vía especificación, proveedor o solución constructiva.",
      "Conviene validar con trazabilidad documental antes de cerrar decisión.",
    ],
    actionLabel: "Revisar problemas",
    actionTo: "/problemas",
  },
  {
    id: "signal-3",
    title: "Reducir factor de Acero estructural en 15%",
    priority: "media",
    summary:
      "Escenario intermedio que muestra un potencial de mejora superior manteniendo una implementación razonable.",
    area: "Materiales",
    nextStep:
      "Revisar compatibilidad técnica de la alternativa y su trazabilidad documental.",
    details: [
      "Representa un escenario comparativo para revisión.",
      "Debe contrastarse con costo, disponibilidad y desempeño esperado.",
      "Aún no constituye una acción aprobada.",
    ],
    actionLabel: "Revisar problemas",
    actionTo: "/problemas",
  },
  {
    id: "signal-4",
    title: "Reducir factor de Acero estructural en 20%",
    priority: "media",
    summary:
      "Escenario ambicioso de reducción que permite visualizar el techo potencial de mejora.",
    area: "Materiales",
    nextStep:
      "Validar si la alternativa mantiene viabilidad técnica y operativa.",
    details: [
      "Se plantea como comparación avanzada, no como decisión cerrada.",
      "Conviene revisar sensibilidad de costo y disponibilidad.",
      "Útil para priorizar análisis más profundos.",
    ],
    actionLabel: "Revisar problemas",
    actionTo: "/problemas",
  },
  {
    id: "signal-5",
    title: "Evaluar proveedor alternativo para Acero estructural",
    priority: "media",
    summary:
      "Escenario conservador de 10% por alternativa técnica o proveedor, con impacto atractivo y baja complejidad inicial.",
    area: "Materiales",
    nextStep:
      "Comparar desempeño ambiental, respaldo documental y costo operacional.",
    details: [
      "Proveedor frecuente: Proveedor demo.",
      "Fuente analizada: Acero estructural.",
      "La oportunidad depende de validar evidencia y consistencia de abastecimiento.",
    ],
    actionLabel: "Revisar problemas",
    actionTo: "/problemas",
  },
];

const recommendations = [
  {
    id: "recommendation-1",
    title: "Completar dato base para Huella total obra",
    priority: "media",
    description:
      "Captura el dato base faltante desde documento, variable o registro operacional verificable.",
    origin: "Huella total obra",
    context:
      "Definir fuente oficial del dato y periodicidad de carga para asegurar trazabilidad.",
    impact:
      "Habilita intensidad ambiental real y comparabilidad entre períodos o unidades operativas.",
  },
  {
    id: "recommendation-2",
    title: "Completar dato base para Combustible consumido",
    priority: "baja",
    description:
      "Falta registrar el dato base asociado al combustible consumido para consolidar la lectura operacional.",
    origin: "Combustible consumido",
    context:
      "Definir fuente oficial del dato y periodicidad de carga.",
    impact:
      "Mejora la comparabilidad entre períodos y habilita métricas más confiables.",
  },
  {
    id: "recommendation-3",
    title: "Completar dato base para RCD generado",
    priority: "baja",
    description:
      "Captura el dato base faltante desde documento, variable o registro operacional verificable.",
    origin: "RCD generado",
    context:
      "Definir fuente oficial del dato y periodicidad de carga.",
    impact:
      "Habilita intensidad ambiental real y comparabilidad entre períodos o unidades operativas.",
  },
];

const scenarios = [
  {
    id: "scenario-1",
    title: "Reducir factor de Acero estructural en 10%",
    status: "disponible",
    description:
      "Basado en emisiones reales de Acero estructural.",
    estimatedImpact: "60036.57 kgCO2e",
    focus:
      "Escenario prudente para iniciar comparación técnica y económica.",
    reviewPoints: [
      "Disponibilidad de proveedor o alternativa.",
      "Respaldo documental y trazabilidad.",
      "Impacto en costo operacional.",
    ],
  },
  {
    id: "scenario-2",
    title: "Reducir factor de Acero estructural en 15%",
    status: "disponible",
    description:
      "Basado en emisiones reales de Acero estructural.",
    estimatedImpact: "56701.21 kgCO2e",
    focus:
      "Escenario intermedio para explorar una reducción más agresiva.",
    reviewPoints: [
      "Viabilidad técnica del cambio.",
      "Comparación costo-beneficio.",
      "Sostenibilidad del abastecimiento.",
    ],
  },
  {
    id: "scenario-3",
    title: "Reducir factor de Acero estructural en 20%",
    status: "disponible",
    description:
      "Basado en emisiones reales de Acero estructural.",
    estimatedImpact: "53365.84 kgCO2e",
    focus:
      "Escenario de alto potencial para análisis profundo y priorización.",
    reviewPoints: [
      "Factibilidad operativa real.",
      "Riesgo de implementación.",
      "Soporte documental y técnico.",
    ],
  },
];

function toneForPriority(priority) {
  switch (priority) {
    case "alta":
      return "danger";
    case "media":
      return "info";
    case "baja":
      return "neutral";
    default:
      return "neutral";
  }
}

function labelForPriority(priority) {
  switch (priority) {
    case "alta":
      return "Alta";
    case "media":
      return "Media";
    case "baja":
      return "Baja";
    default:
      return "Sin prioridad";
  }
}

function toneForScenario(status) {
  switch (status) {
    case "disponible":
      return "success";
    case "en_revision":
      return "warning";
    default:
      return "neutral";
  }
}

function labelForScenario(status) {
  switch (status) {
    case "disponible":
      return "Disponible";
    case "en_revision":
      return "En revisión";
    default:
      return "Sin estado";
  }
}

function IntelligenceSignalCard({
  item,
}) {
  return (
    <article className="rounded-[22px] border border-emerald-100 bg-white p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)] transition hover:-translate-y-0.5 hover:shadow-[0_18px_38px_rgba(15,23,42,0.08)]">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-lg font-black text-[var(--text-primary)]">
              {item.title}
            </h3>

            <StatusBadge tone={toneForPriority(item.priority)}>
              {labelForPriority(item.priority)}
            </StatusBadge>
          </div>

          <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">
            {item.summary}
          </p>

          <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs text-[var(--text-muted)]">
            <span>
              <b className="text-[var(--text-secondary)]">Área:</b>{" "}
              {item.area}
            </span>

            <span>
              <b className="text-[var(--text-secondary)]">Siguiente paso:</b>{" "}
              {item.nextStep}
            </span>
          </div>

          <details className="mt-4 group">
            <summary className="cursor-pointer list-none text-sm font-bold text-emerald-800 transition hover:text-emerald-700">
              <span className="inline-flex items-center gap-2">
                <ChevronRight
                  className="transition group-open:rotate-90"
                  size={16}
                />
                Detalles considerados
              </span>
            </summary>

            <ul className="mt-3 space-y-2 pl-6 text-sm text-[var(--text-secondary)]">
              {item.details.map((detail) => (
                <li
                  key={detail}
                  className="list-disc"
                >
                  {detail}
                </li>
              ))}
            </ul>
          </details>
        </div>

        <div className="shrink-0">
          <Link to={item.actionTo}>
            <Button variant="ghost">
              {item.actionLabel}
            </Button>
          </Link>
        </div>
      </div>
    </article>
  );
}

function RecommendationCard({
  item,
}) {
  return (
    <article className="rounded-[22px] border border-slate-200 bg-white p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)] transition hover:-translate-y-0.5 hover:shadow-[0_18px_38px_rgba(15,23,42,0.08)]">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-base font-black leading-6 text-[var(--text-primary)]">
          {item.title}
        </h3>

        <StatusBadge tone={toneForPriority(item.priority)}>
          {labelForPriority(item.priority)}
        </StatusBadge>
      </div>

      <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">
        {item.description}
      </p>

      <div className="mt-4 space-y-2 text-xs leading-5 text-[var(--text-muted)]">
        <p>
          <b className="text-[var(--text-secondary)]">Origen:</b>{" "}
          {item.origin}
        </p>

        <p>
          <b className="text-[var(--text-secondary)]">Decisión a revisar:</b>{" "}
          {item.context}
        </p>

        <p>
          <b className="text-[var(--text-secondary)]">Impacto esperado:</b>{" "}
          {item.impact}
        </p>
      </div>

      <div className="mt-4">
        <Link
          to="/problemas"
          className="inline-flex items-center gap-2 text-sm font-bold text-emerald-800 transition hover:text-emerald-700"
        >
          Ver contexto
          <ArrowRight size={16} />
        </Link>
      </div>
    </article>
  );
}

function ScenarioCard({
  item,
}) {
  return (
    <article className="rounded-[22px] border border-slate-200 bg-white p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)] transition hover:-translate-y-0.5 hover:shadow-[0_18px_38px_rgba(15,23,42,0.08)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h3 className="text-base font-black leading-6 text-[var(--text-primary)]">
          {item.title}
        </h3>

        <StatusBadge tone={toneForScenario(item.status)}>
          {labelForScenario(item.status)}
        </StatusBadge>
      </div>

      <p className="mt-3 text-sm text-[var(--text-secondary)]">
        {item.description}
      </p>

      <div className="mt-4 rounded-2xl border border-emerald-100 bg-emerald-50/70 px-4 py-3">
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-emerald-800">
          Impacto estimado
        </p>
        <p className="mt-1 text-2xl font-black text-emerald-900">
          {item.estimatedImpact}
        </p>
      </div>

      <p className="mt-4 text-sm leading-6 text-[var(--text-secondary)]">
        {item.focus}
      </p>

      <details className="mt-4 group">
        <summary className="cursor-pointer list-none text-sm font-bold text-emerald-800 transition hover:text-emerald-700">
          <span className="inline-flex items-center gap-2">
            <ChevronRight
              className="transition group-open:rotate-90"
              size={16}
            />
            Qué revisar
          </span>
        </summary>

        <ul className="mt-3 space-y-2 pl-6 text-sm text-[var(--text-secondary)]">
          {item.reviewPoints.map((point) => (
            <li
              key={point}
              className="list-disc"
            >
              {point}
            </li>
          ))}
        </ul>
      </details>
    </article>
  );
}

export default function IntelligencePage() {
  const summary = useMemo(
    () => ({
      signals: attentionSignals.length,
      recommendations: recommendations.length,
      scenarios: scenarios.length,
    }),
    []
  );

  return (
    <main className="space-y-6">
      <section className="overflow-hidden rounded-[28px] border border-emerald-700/20 bg-[linear-gradient(135deg,rgba(6,78,59,0.97)_0%,rgba(6,95,70,0.93)_48%,rgba(15,118,110,0.84)_100%)] p-6 text-white shadow-[0_18px_45px_rgba(6,78,59,0.16)]">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-100">
              Gestión ambiental · Inteligencia
            </p>

            <h1 className="mt-2 text-3xl font-black">
              Inteligencia
            </h1>

            <p className="mt-2 max-w-2xl text-sm leading-6 text-emerald-50/85">
              Señales y análisis que ayudan a identificar dónde profundizar,
              qué revisar primero y qué oportunidades tienen mayor potencial
              para transformarse en decisiones ambientales verificables.
            </p>

            <div className="mt-4 flex flex-wrap gap-2">
              <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold">
                {summary.signals} señales activas
              </span>

              <span className="rounded-full border border-emerald-200/30 bg-emerald-200/10 px-3 py-1.5 text-xs font-bold text-emerald-50">
                {summary.recommendations} recomendaciones
              </span>

              <span className="rounded-full border border-amber-300/40 bg-amber-300/15 px-3 py-1.5 text-xs font-bold text-amber-100">
                {summary.scenarios} escenarios disponibles
              </span>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link to="/problemas">
              <Button variant="secondary">
                <TriangleAlert size={18} />
                Ver problemas
              </Button>
            </Link>

            <Link to="/copiloto">
              <Button className="shadow-[0_8px_24px_rgba(0,0,0,0.14)]">
                <Bot size={18} />
                Abrir Copiloto
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">
            Priorización
          </p>
          <h2 className="mt-1 text-2xl font-black text-[var(--text-primary)]">
            Qué merece atención
          </h2>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Prioridades construidas a partir de señales y datos disponibles.
          </p>
        </div>

        {attentionSignals.length ? (
          <div className="space-y-4">
            {attentionSignals.map((item) => (
              <IntelligenceSignalCard
                key={item.id}
                item={item}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            icon={Sparkles}
            title="No hay señales activas"
            description="Cuando existan hallazgos o patrones relevantes, aparecerán aquí para ser priorizados."
            className="border-emerald-200/80 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.14),transparent_40%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] shadow-[0_12px_36px_rgba(6,78,59,0.06)]"
          />
        )}
      </section>

      <section className="space-y-4">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">
            Apoyo a decisión
          </p>
          <h2 className="mt-1 text-2xl font-black text-[var(--text-primary)]">
            Recomendaciones
          </h2>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Alternativas sugeridas para revisar; todavía no son acciones implementadas.
          </p>
        </div>

        {recommendations.length ? (
          <div className="grid gap-4 xl:grid-cols-3">
            {recommendations.map((item) => (
              <RecommendationCard
                key={item.id}
                item={item}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            icon={Lightbulb}
            title="No hay recomendaciones disponibles"
            description="Las recomendaciones aparecerán cuando el sistema detecte brechas de datos u oportunidades de mejora."
            className="border-emerald-200/80 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.14),transparent_40%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] shadow-[0_12px_36px_rgba(6,78,59,0.06)]"
          />
        )}
      </section>

      <section className="space-y-4">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">
            Exploración
          </p>
          <h2 className="mt-1 text-2xl font-black text-[var(--text-primary)]">
            Escenarios disponibles
          </h2>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Comparaciones para explorar después de revisar las señales principales.
          </p>
        </div>

        {scenarios.length ? (
          <div className="grid gap-4 xl:grid-cols-3">
            {scenarios.map((item) => (
              <ScenarioCard
                key={item.id}
                item={item}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            icon={Target}
            title="No hay escenarios disponibles"
            description="Cuando exista base suficiente para comparar alternativas, aparecerán aquí."
            className="border-emerald-200/80 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.14),transparent_40%),linear-gradient(135deg,rgba(236,253,245,0.98),rgba(255,255,255,0.98))] shadow-[0_12px_36px_rgba(6,78,59,0.06)]"
          />
        )}
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <article className="rounded-[22px] border border-slate-200 bg-white p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)]">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700">
              <Sparkles size={20} />
            </div>
            <div>
              <p className="text-sm font-black text-[var(--text-primary)]">
                Lectura actual
              </p>
              <p className="text-xs text-[var(--text-muted)]">
                Señales disponibles
              </p>
            </div>
          </div>

          <p className="mt-4 text-sm leading-6 text-[var(--text-secondary)]">
            La vista está orientada a priorizar revisión, no a ejecutar acciones
            automáticamente.
          </p>
        </article>

        <article className="rounded-[22px] border border-slate-200 bg-white p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)]">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-amber-50 text-amber-700">
              <TriangleAlert size={20} />
            </div>
            <div>
              <p className="text-sm font-black text-[var(--text-primary)]">
                Siguiente paso sugerido
              </p>
              <p className="text-xs text-[var(--text-muted)]">
                Prioriza la revisión
              </p>
            </div>
          </div>

          <p className="mt-4 text-sm leading-6 text-[var(--text-secondary)]">
            Revisa primero las señales con mayor impacto potencial y luego contrasta
            escenarios y recomendaciones.
          </p>
        </article>

        <article className="rounded-[22px] border border-slate-200 bg-white p-5 shadow-[0_10px_30px_rgba(15,23,42,0.05)]">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-sky-50 text-sky-700">
              <CheckCircle2 size={20} />
            </div>
            <div>
              <p className="text-sm font-black text-[var(--text-primary)]">
                Enfoque del módulo
              </p>
              <p className="text-xs text-[var(--text-muted)]">
                Inteligencia asistida
              </p>
            </div>
          </div>

          <p className="mt-4 text-sm leading-6 text-[var(--text-secondary)]">
            Este módulo ayuda a enfocar atención; la decisión final y la validación
            siguen estando gobernadas por la trazabilidad del sistema.
          </p>
        </article>
      </section>
    </main>
  );
}
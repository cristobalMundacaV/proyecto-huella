import {
  useEffect,
  useState,
} from "react";

import {
  Activity,
  History,
  TrendingUp,
} from "lucide-react";

import {
  useOutletContext,
} from "react-router-dom";

import {
  EmptyState,
  KpiCard,
  SectionHeader,
  StatusBadge,
  TableBody,
  TableCell,
  TableHead,
  TableShell,
} from "@/shared/ui";

import {
  formatDateTime,
  formatNumber,
} from "@/shared/utils/formatters";

import {
  getBaselines,
  getEnvironmentalImpacts,
  getIndicators,
} from "@/features/operacion/api/calculationApi";


const human = (value) =>
  String(
    value || "",
  ).replaceAll(
    "_",
    " ",
  );


export default function ObraIndicatorsPage() {
  const {
    obra,
    context,
  } = useOutletContext();

  const workId =
    obra?.id ||
    obra?.obra_id;

  const organizationId =
    context
      ?.references
      ?.organization;

  const [
    state,
    setState,
  ] = useState({
    loading: true,
    indicators: [],
    baselines: [],
    impacts: [],
  });

  useEffect(
    () => {
      if (
        !organizationId ||
        !workId
      ) {
        return;
      }

      Promise.all([
        getIndicators(
          organizationId,
          {
            obra: workId,
          },
        ),

        getBaselines(
          organizationId,
          {
            obra: workId,
          },
        ),

        getEnvironmentalImpacts(
          organizationId,
          {
            obra: workId,
          },
        ),
      ]).then(
        ([
          indicators,
          baselines,
          impacts,
        ]) => {
          setState({
            loading: false,
            indicators,
            baselines,
            impacts,
          });
        },
      );
    },
    [
      organizationId,
      workId,
    ],
  );

  if (
    state.loading
  ) {
    return (
      <p className="text-sm text-[var(--text-muted)]">
        Cargando indicadores...
      </p>
    );
  }

  const availableIndicators = state.indicators.filter((indicator) => indicator.valor_actual?.valor !== null && indicator.valor_actual?.valor !== undefined);
  const baselineByIndicator = new Map(state.baselines.map((baseline) => [String(baseline.indicador), baseline]));
  const noEnvironmentalData = !availableIndicators.length && !state.baselines.length && !state.impacts.length;

  return (
    <section className="space-y-6">
      <SectionHeader
        eyebrow="LECTURA AMBIENTAL"
        title="Indicadores"
        description="Resultados ambientales versionados y scoped exclusivamente a esta obra."
      />

      {noEnvironmentalData ? <EmptyState
        icon={Activity}
        title="Sin lectura ambiental disponible"
        description="Esta obra todavía no tiene valores, líneas base ni resultados calculados suficientes para construir una lectura de indicadores."
      /> : <>

      {availableIndicators.length ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {availableIndicators.slice(0, 4).map(
            (indicator) => (
              <KpiCard
                key={
                  indicator.id
                }
                label={
                  indicator.nombre
                }
                value={
                  indicator
                    .valor_actual
                    ?.valor
                }
                unit={
                  indicator.unidad
                }
                helper={
                  baselineByIndicator.has(String(indicator.id))
                    ? `Línea base ${human(baselineByIndicator.get(String(indicator.id)).estado)}`
                    : `${human(indicator.tipo)} · Sin línea base disponible`
                }
                icon={
                  Activity
                }
              />
            ),
          )}
        </div>
      ) : (
        <EmptyState
          icon={Activity}
          title="Aún no hay indicadores"
          description="Los indicadores aparecerán cuando existan resultados gobernados suficientes."
        />
      )}

      <div className="space-y-3">
        <SectionHeader
          eyebrow="LÍNEA BASE"
          title="Bases comparables"
          description="Una línea base se construye con historia real; no se inventa cuando faltan períodos."
        />

        {!state.baselines.length ? (
          <EmptyState
            icon={History}
            title="Línea base en construcción"
            description="Todavía no existe historia suficiente para establecer una referencia."
          />
        ) : (
          <TableShell>
            <TableHead>
              <tr>
                <TableCell as="th">
                  Indicador
                </TableCell>

                <TableCell as="th">
                  Estado
                </TableCell>

                <TableCell as="th">
                  Valor base
                </TableCell>

                <TableCell as="th">
                  Períodos
                </TableCell>
              </tr>
            </TableHead>

            <TableBody
              columns={4}
            >
              {state.baselines.map(
                (
                  baseline,
                ) => (
                  <tr
                    key={
                      baseline.id
                    }
                  >
                    <TableCell>
                      {
                        baseline.indicador_nombre
                      }
                    </TableCell>

                    <TableCell>
                      <StatusBadge>
                        {human(
                          baseline.estado,
                        )}
                      </StatusBadge>
                    </TableCell>

                    <TableCell>
                      {baseline.valor_base ===
                        null
                        ? "Sin base"
                        : formatNumber(
                          baseline.valor_base,
                        )}
                    </TableCell>

                    <TableCell>
                      {
                        baseline.cantidad_periodos
                      }
                    </TableCell>
                  </tr>
                ),
              )}
            </TableBody>
          </TableShell>
        )}
      </div>

      <div className="space-y-3">
        <SectionHeader
          eyebrow="IMPACTOS"
          title="Resultados calculados"
          description="Cada resultado mantiene referencia al cálculo y actividad que lo originaron."
        />

        {!state.impacts.length ? (
          <EmptyState
            icon={TrendingUp}
            title="Sin impactos calculados"
            description="Aún no existen resultados de cálculo para esta obra."
          />
        ) : (
          <TableShell>
            <TableHead>
              <tr>
                <TableCell as="th">
                  Actividad
                </TableCell>

                <TableCell as="th">
                  Categoría
                </TableCell>

                <TableCell as="th">
                  Resultado
                </TableCell>

                <TableCell as="th">
                  Fecha
                </TableCell>
              </tr>
            </TableHead>

            <TableBody
              columns={4}
            >
              {state.impacts.map(
                (
                  impact,
                ) => (
                  <tr
                    key={
                      impact.id
                    }
                  >
                    <TableCell>
                      {
                        impact.actividad_nombre
                      }
                    </TableCell>

                    <TableCell>
                      {human(
                        impact.categoria,
                      )}
                    </TableCell>

                    <TableCell>
                      <b>
                        {formatNumber(
                          impact.valor,
                        )}{" "}
                        {
                          impact.unidad
                        }
                      </b>
                    </TableCell>

                    <TableCell>
                      {formatDateTime(
                        impact.timestamp,
                      )}
                    </TableCell>
                  </tr>
                ),
              )}
            </TableBody>
          </TableShell>
        )}
      </div>
      </>}
    </section>
  );
}

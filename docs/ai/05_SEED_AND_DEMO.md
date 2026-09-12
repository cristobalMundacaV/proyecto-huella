# AI-INTELLIGENCE-01 — Seed de demostración

## Comando

```sh
python manage.py seed_ai_demo_tenant [--reset]
```

Empresa 100% sintética: **Constructora Horizonte Demo SpA**
(`organizacion_id=DEMO_HORIZONTE`). El repositorio principal es público
(`docs/ai-context/08_TENANCY_RBAC_SECURITY.md`) — este tenant nunca
contiene datos reales de clientes.

## Qué crea

- 1 organización + 1 usuario admin (`demo-horizonte-admin`, sin contraseña
  utilizable por defecto — sólo un actor de datos, no una cuenta de login
  real) con membresía `ADMIN`.
- 2 obras ("Edificio Horizonte Norte", "Condominio Horizonte Sur").
- 6 materiales (hormigón, acero, diésel, electricidad, agua, residuos),
  cada uno con su propio `FactorAmbiental`/`VersionFactorAmbiental` llevado
  a estado `activo` vía la gobernanza real (`transition_factor_version`) y
  mapeado vía `propose_material_mapping`/`approve_material_mapping` —
  excepto el hormigón, mapeado en cambio mediante una cadena EC3 real
  (ver abajo).
- 4 meses de historial de actividades/observaciones/`EventoMaterial` por
  material, calculados con el motor real (`calculate_activity`) — nunca
  números insertados directamente.
- Indicadores ambientales v2: uno con historial de 4 períodos
  (`co2e_total_demo`) y **uno deliberadamente sin ningún valor**
  (`agua_intensidad_demo`) — para probar que el asistente dice "no tengo
  esa información" en vez de inventar una tendencia.
- 1 alerta abierta (`ProblematicaAmbiental`, riesgo alto, sobre el
  hotspot de hormigón) — el "alerta" moderno de este sistema.
- 1 hotspot real: el hormigón concentra ~93.8% del impacto positivo total
  (cantidad deliberadamente mayor que el resto).
- Un material con mapping EC3 real y gobernado: se ingiere una EPD
  sintética ("demohrz1", vía `Ec3Client` con una sesión HTTP simulada —
  nunca una llamada de red real), se revisa, promueve, transiciona y
  mapea igual que en producción (mismo código: `ingest_epd`,
  `review_candidate`, `promote_candidate`, `propose_mapping`,
  `approve_material_mapping`).
- Una oportunidad EC3 potencial comparable: un segundo EPD sintético más
  barato ("demohrz2") se propone para el mismo material pero **nunca se
  promueve ni mapea** — queda como candidato pre-decisional, visible vía
  `get_ec3_opportunities`/`apps.ec3.opportunity.material_candidate_opportunities`.
- Un dato deliberadamente incompleto: el material de agua no tiene
  observación en el mes más reciente — el asistente debe decir que no hay
  datos de ese período, nunca interpolar.

## Comportamiento del estado EC3 según configuración

El material de hormigón participa en la gobernanza EC3 real: si
`EC3_ENABLED=false` (default de este entorno), su estado se reporta como
`STALE` y sus oportunidades como no elegibles (`ec3_disabled`) — esto es
correcto, no un error del seed: EC3 exige su propia configuración de
licencia/habilitación (igual que en producción) independientemente de
que el dato demo exista. Con `EC3_ENABLED=true`,
`EC3_STORAGE_ALLOWED=true` y derechos vigentes configurados, el mismo
material se reporta `MAPPED` y la oportunidad muestra una reducción
potencial real. Ver `docs/integrations/ec3/03_OPERATIONS.md`.

## Idempotencia

Seguro de re-ejecutar. `--reset` limpia únicamente alertas, indicadores/
valores y conversaciones (regenerables); nunca intenta borrar actividades/
cálculos históricos ni evidencia EC3 — `CalculoAmbiental` está protegido
por `ImpactoAmbiental`/`InputCalculoAmbiental`/`EvaluacionCalidadDato`, y
`Review`/`EpdVersion` son inmutables por diseño (la misma garantía de
gobernanza EC3 verificada en EC3-01) — intentar borrarlos fallaría, y de
todas formas es innecesario: cada paso de creación ya comprueba existencia
antes de crear, así que re-ejecutar sin `--reset` simplemente confirma lo
que ya existe sin duplicar nada.

Probado en `apps/ai/tests/test_seed_command.py` (ejecuta el comando dos
veces seguidas y verifica que no falla ni duplica).

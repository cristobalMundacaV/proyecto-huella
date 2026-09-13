import {
    ArrowLeft,
    Boxes,
    Building2,
    Check,
    ChevronDown,
    Loader2,
} from "lucide-react";

import {
    useEffect,
    useMemo,
    useState,
} from "react";

import {
    NavLink,
    useLocation,
    useNavigate,
} from "react-router-dom";

import {
    getObraContextualSubnav,
    getUnifiedNavigation,
} from "@/app/navigation";

import {
    useOrganizacionActiva,
} from "@/features/organizaciones/context/OrganizacionActivaContext";

import {
    getActivePreset,
    getPresetLabel,
} from "@/presets/registry";
import { getOrganizacionObras } from "@/shared/services/api";
import { getEnvironmentalDomain } from "@/shared/config/environmentalDomains";
import { usePermissions } from "@/features/auth/hooks/usePermissions";
import { useOperationalWorkspace } from "@/features/workspace/context/OperationalWorkspaceContext";
import { getWorkContext } from "@/features/obras/services/workspaceApi";
import { prefetchWork } from "@/features/obras/services/workspacePrefetch";
import { withObraFlowStates } from "@/app/obraSubnavVisibility";

const ATTENTION_STATES = new Set(["requiere_atencion", "cierre_pendiente"]);
const STABLE_STATES = new Set(["estable", "monitoreo", "mejora_en_curso", "cerrada"]);

function workAttentionDot(work) {
    const status = work?.estado_ambiental;
    if (ATTENTION_STATES.has(status)) return "bg-amber-500";
    if (STABLE_STATES.has(status)) return "bg-emerald-500";
    return "bg-slate-300";
}

const NAV_PERMISSIONS = {
    administration: "settings.view", professionalReview: "professional_review.execute",
    imports: "imports.view", evidence: "evidence.view", indicators: "indicators.view",
    compliance: "compliance.view", problems: "problems.view", improvement: "problems.view",
    reports: "reports.view", assets: "assets.view", sensors: "sensors.view", audit: "audit.view",
};

function filterNavigation(navigation, can) {
    return {
        ...navigation,
        groups: navigation.groups.map((group) => ({
            ...group,
            items: group.items.filter((item) => !NAV_PERMISSIONS[item.id] || can(NAV_PERMISSIONS[item.id])),
        })).filter((group) => group.items.length),
    };
}


function resolveWorkId(
    pathname
) {
    const match =
        pathname.match(
            /^\/obras\/([^/]+)(?:\/|$)/
        );

    return match?.[1] || null;
}


export default function Sidebar({
    onNavigate,
}) {
    const { can } = usePermissions();
    const { activeWorkspace, exitWorkspace } = useOperationalWorkspace();
    const navigate =
        useNavigate();

    const {
        pathname,
    } = useLocation();

    const {
        activeOrganizacion,
        activeOrganizacionId,
        clearActiveOrganizacion,
        organizaciones,
        loadingOrganizaciones,
        setActiveOrganizacion,
    } = useOrganizacionActiva();


    const presetKey =
        activeOrganizacion?.preset ||
        "construccion";

    const preset =
        useMemo(
            () =>
                getActivePreset(
                    presetKey
                ),
            [presetKey]
        );


    const workId =
        resolveWorkId(
            pathname
        );

    const scope = useMemo(
        () => (workId ? { type: "obra", obraId: workId } : { type: "portfolio" }),
        [workId],
    );

    const navigation =
        useMemo(
            () => filterNavigation(getUnifiedNavigation({ preset, scope }), can),
            [can, preset, scope]
        );

    // Obra-level applicability (aplica/pendiente/no_aplica per flow), fetched
    // once per obra — powers ONLY the "OBRA ACTIVA" subnav's visibility/dot
    // below; it never re-introduces a second sidebar, just decides which of
    // the always-existing operation routes get a mini status dot and which
    // (only `no_aplica`) are left out.
    const applicabilityScope = activeOrganizacionId && workId ? `${activeOrganizacionId}:${workId}` : "";
    const [workApplicability, setWorkApplicability] = useState({ scope: "", rows: [] });

    useEffect(() => {
        let active = true;
        if (!applicabilityScope) {
            setWorkApplicability({ scope: "", rows: [] });
            return () => { active = false; };
        }
        setWorkApplicability({ scope: applicabilityScope, rows: [] });
        getWorkContext(activeOrganizacionId, workId)
            .then((workspace) => {
                if (!active) return;
                const rows = workspace?.context?.diagnostico_obra?.aplicabilidad;
                const organizationCapabilities = workspace?.context?.capacidades_organizacion;
                const enabledKeys = new Set(
                    (Array.isArray(organizationCapabilities) ? organizationCapabilities : [])
                        .filter((item) => item?.estado_organizacion !== "no_aplica")
                        .map((item) => item?.clave),
                );
                setWorkApplicability({
                    scope: applicabilityScope,
                    rows: (Array.isArray(rows) ? rows : []).filter((item) => enabledKeys.has(item?.clave)),
                });
            })
            .catch(() => {
                if (active) setWorkApplicability({ scope: applicabilityScope, rows: [] });
            });
        return () => { active = false; };
    }, [activeOrganizacionId, applicabilityScope, workId]);

    useEffect(() => {
        const updateApplicability = (event) => {
            const detail = event.detail || {};
            if (String(detail.organizationId) !== String(activeOrganizacionId) || String(detail.workId) !== String(workId)) return;
            setWorkApplicability((current) => ({
                ...current,
                rows: current.rows.map((item) => item.clave === detail.key ? { ...item, estado_obra: detail.estado } : item),
            }));
        };
        window.addEventListener("carbono-zero:work-applicability-updated", updateApplicability);
        return () => window.removeEventListener("carbono-zero:work-applicability-updated", updateApplicability);
    }, [activeOrganizacionId, workId]);

    const applicabilityRows = useMemo(
        () => (workApplicability.scope === applicabilityScope ? workApplicability.rows : []),
        [applicabilityScope, workApplicability],
    );

    const obraSubnav = useMemo(() => {
        if (!workId) return null;
        const subnav = filterNavigation(getObraContextualSubnav(workId), can);
        return withObraFlowStates(subnav, applicabilityRows);
    }, [applicabilityRows, can, workId]);


    const exactPaths =
        useMemo(() => {
            const paths = [
                navigation.home?.path,

                ...navigation.groups.flatMap(
                    group =>
                        group.items.flatMap(
                            item =>
                                item.children?.length
                                    ? item.children.map(
                                        child =>
                                            child.path
                                    )
                                    : [
                                        item.path,
                                    ]
                        )
                ),
            ].filter(Boolean);

            return new Set(
                paths.filter(
                    path =>
                        paths.some(
                            other =>
                                other !== path &&
                                other.startsWith(
                                    `${path}/`
                                )
                        )
                )
            );
        }, [
            navigation,
        ]);


    const [
        expanded,
        setExpanded,
    ] = useState({});


    useEffect(() => {
        const next = {};

        navigation.groups.forEach(
            group =>
                group.items.forEach(
                    item => {
                        if (
                            item.children?.some(
                                child =>
                                    pathname.startsWith(
                                        child.path
                                    )
                            )
                        ) {
                            next[item.id] =
                                true;
                        }
                    }
                )
        );

        setExpanded(next);
    }, [
        navigation.groups,
        pathname,
    ]);


    function switchOrganization(
        event
    ) {
        const selected =
            organizaciones.find(
                org =>
                    String(
                        org.organizacion_id
                    ) ===
                    event.target.value
            );

        if (selected) {
            setActiveOrganizacion(
                selected
            );

            navigate(
                "/inicio"
            );
        } else {
            clearActiveOrganizacion();
        }

        onNavigate?.();
    }

    function returnToGeneralView() {
        exitWorkspace();
        navigate("/inicio");
        onNavigate?.();
    }

    const simplified = activeWorkspace && !workId && !["medio_ambiente", "gestion_obra"].includes(activeWorkspace.area.tipo);
    if (simplified) return <aside className="flex min-h-full w-full shrink-0 flex-col border-r border-[var(--sidebar-border)] bg-[var(--sidebar)] px-3 py-5 lg:sticky lg:top-[72px] lg:h-[calc(100vh-72px)] lg:w-64"><button type="button" onClick={returnToGeneralView} className="mb-4 flex w-full items-center gap-2 rounded-xl border border-emerald-200 bg-white px-3 py-2.5 text-left text-sm font-black text-emerald-800 shadow-sm transition hover:border-emerald-300 hover:bg-emerald-50 focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"><ArrowLeft aria-hidden="true" size={17} />Volver a vista general</button><div className="mb-6 rounded-2xl bg-emerald-50 p-4"><p className="text-xs font-black uppercase tracking-wide text-emerald-700">{activeWorkspace.area.nombre}</p><p className="mt-1 text-sm font-bold text-slate-800">{activeWorkspace.obra?.nombre || activeWorkspace.organizacion.nombre}</p></div><nav className="space-y-1"><NavLink end to="/inicio" onClick={onNavigate} className={({ isActive }) => `block rounded-xl px-3 py-2.5 text-sm font-bold ${isActive ? "bg-emerald-100 text-emerald-900" : "text-slate-700 hover:bg-slate-100"}`}>Inicio</NavLink><a href="/inicio#subir-informacion" className="block rounded-xl px-3 py-2.5 text-sm font-bold text-slate-700 hover:bg-slate-100">Subir información</a><a href="/inicio#ultimos-envios" className="block rounded-xl px-3 py-2.5 text-sm font-bold text-slate-700 hover:bg-slate-100">Documentos enviados</a><a href="/inicio#pendientes" className="block rounded-xl px-3 py-2.5 text-sm font-bold text-slate-700 hover:bg-slate-100">Pendientes</a></nav></aside>;

    return (
        <aside className="flex min-h-full w-full shrink-0 flex-col border-b border-[var(--sidebar-border)] bg-[var(--sidebar)] px-3 py-4 text-[var(--text-main)] shadow-[18px_0_50px_rgba(19,34,56,0.05)] lg:sticky lg:top-[72px] lg:h-[calc(100vh-72px)] lg:w-64 lg:border-b-0 lg:border-r">

            <OrganizationSelector
                activeOrganizacionId={
                    activeOrganizacionId
                }
                organizaciones={
                    organizaciones
                }
                loadingOrganizaciones={
                    loadingOrganizaciones
                }
                presetKey={
                    presetKey
                }
                onChange={
                    switchOrganization
                }
            />

            <ContextSelector
                activeOrganizacionId={activeOrganizacionId}
                onNavigate={onNavigate}
                preset={preset}
                scope={scope}
            />

            {/* ONE scrollable region for BOTH the primary nav and the obra
                subnav — this is the fix: `GeneralNavigation`'s <nav> used to
                carry `flex-1` on its own, growing to fill the aside and
                pushing `ObraActiveSubnav` (its next DOM sibling) all the way
                to the bottom behind a huge empty gap. Now `flex-1`/scroll
                live on this wrapper only, so the subnav sits immediately
                after the primary nav in normal document flow. */}
            <div className="min-h-0 flex-1 overflow-y-auto px-1 pb-2">
                <GeneralNavigation
                    navigation={
                        navigation
                    }
                    expanded={
                        expanded
                    }
                    setExpanded={
                        setExpanded
                    }
                    exactPaths={
                        exactPaths
                    }
                    onNavigate={
                        onNavigate
                    }
                />

                {obraSubnav && (
                    <ObraActiveSubnav
                        onNavigate={onNavigate}
                        pathname={pathname}
                        subnav={obraSubnav}
                    />
                )}
            </div>
        </aside>
    );
}


const FLOW_STATE_DOT = {
    aplica: "bg-current",
    pendiente: "border border-current bg-transparent",
};

/** The compact "OBRA ACTIVA" subnav — rendered UNDER the same five unified
 * items, never a second sidebar. Two collapsible groups (Operación,
 * Gestión); whichever contains the active route starts expanded. Every
 * `path` here is an existing route (see router.jsx) — this component only
 * decides what's visible/expanded, never creates a page. */
function activeGroupFor(subnav, pathname) {
    return subnav.groups.find((group) => group.items.some((item) => pathname === item.path || pathname.startsWith(`${item.path}/`)));
}

function ObraActiveSubnav({ onNavigate, pathname, subnav }) {
    const [expandedGroups, setExpandedGroups] = useState(() => {
        const active = activeGroupFor(subnav, pathname);
        return new Set([active ? active.id : "operation"]);
    });

    useEffect(() => {
        const active = activeGroupFor(subnav, pathname);
        if (active) setExpandedGroups((current) => (current.has(active.id) ? current : new Set([...current, active.id])));
    }, [pathname, subnav]);

    function toggleGroup(id) {
        setExpandedGroups((current) => {
            const next = new Set(current);
            if (next.has(id)) next.delete(id); else next.add(id);
            return next;
        });
    }

    return (
        <nav aria-label="Obra activa" className="mt-3 border-t border-[var(--sidebar-border)] pt-3">
            <p className="mb-1.5 px-2 text-[10px] font-black uppercase tracking-[0.16em] text-[var(--text-muted)]">
                Obra activa
            </p>

            <div className="space-y-2">
                {subnav.groups.map((group) => {
                    const isOpen = expandedGroups.has(group.id);
                    return (
                        <div key={group.id}>
                            <button
                                aria-expanded={isOpen}
                                className="flex w-full items-center gap-2 rounded-[var(--radius-md)] px-2 py-1.5 text-left text-[11px] font-black uppercase tracking-[0.1em] text-[var(--text-muted)] transition hover:bg-[var(--bg-surface-subtle)] hover:text-[var(--text-primary)]"
                                onClick={() => toggleGroup(group.id)}
                                type="button"
                            >
                                <span className="min-w-0 flex-1 truncate">{group.label}</span>
                                <ChevronDown aria-hidden="true" className={`shrink-0 transition ${isOpen ? "rotate-180" : ""}`} size={13} />
                            </button>

                            {isOpen && (
                                <div className="space-y-0.5 pl-1">
                                    {group.items.map((item) => (
                                        <SubnavItem item={item} key={item.id} onNavigate={onNavigate} />
                                    ))}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </nav>
    );
}


function SubnavItem({ item, onNavigate }) {
    const domain = getEnvironmentalDomain(item.domain);
    const Icon = domain?.icon || item.icon;
    const dotStyle = FLOW_STATE_DOT[item.state];

    return (
        <NavLink
            end
            to={item.path}
            onClick={onNavigate}
            className={({ isActive }) =>
                `flex items-center gap-2 rounded-[var(--radius-md)] px-3 py-1.5 text-xs font-bold transition focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] ${isActive
                    ? domain ? `${domain.softBg} ${domain.text}` : "bg-[var(--sidebar-active)] text-[var(--brand-primary)]"
                    : "text-[var(--text-secondary)] hover:bg-[var(--bg-surface-subtle)] hover:text-[var(--text-primary)]"
                }`
            }
        >
            {Icon && <Icon aria-hidden="true" className={domain?.text || ""} size={15} />}
            <span className="min-w-0 flex-1 truncate">{item.label}</span>
            {dotStyle && (
                <span
                    aria-hidden="true"
                    className={`h-1.5 w-1.5 shrink-0 rounded-full ${domain?.text || "text-amber-600"} ${dotStyle}`}
                    title={item.state === "pendiente" ? "Requiere configuración" : "Aplica"}
                />
            )}
        </NavLink>
    );
}


/** ONE-SIDEBAR selector: switches the whole product's context between
 * PORTAFOLIO (the organization) and a single OBRA — never a second,
 * separate sidebar. Same 5 nav items below just change target/content. */
function ContextSelector({
    activeOrganizacionId,
    onNavigate,
    preset,
    scope,
}) {
    const navigate = useNavigate();
    const { pathname } = useLocation();
    const [open, setOpen] = useState(false);
    const [worksState, setWorksState] = useState({ status: "loading", rows: [] });

    useEffect(() => {
        let active = true;
        setOpen(false);
        if (!activeOrganizacionId) {
            setWorksState({ status: "ready", rows: [] });
            return () => { active = false; };
        }
        setWorksState({ status: "loading", rows: [] });
        getOrganizacionObras(activeOrganizacionId)
            .then((data) => {
                if (active) setWorksState({ status: "ready", rows: Array.isArray(data) ? data : data?.results || [] });
            })
            .catch(() => {
                if (active) setWorksState({ status: "error", rows: [] });
            });
        return () => { active = false; };
    }, [activeOrganizacionId]);

    const routeId = (work) => work.id || work.obra_id || work.codigo_obra;
    const isObra = scope.type === "obra";
    const currentWork = isObra ? worksState.rows.find((work) => String(routeId(work)) === String(scope.obraId)) : null;

    function selectPortfolio() {
        setOpen(false);
        if (!isObra) return;
        navigate("/inicio");
        onNavigate?.();
    }

    function selectWork(work) {
        const nextId = routeId(work);
        setOpen(false);
        if (!nextId || String(nextId) === String(scope.obraId)) return;
        const encodedId = encodeURIComponent(nextId);
        const preserved = isObra ? pathname.replace(/^\/obras\/[^/]+/, `/obras/${encodedId}`) : `/obras/${encodedId}/resumen`;
        navigate(preserved.startsWith(`/obras/${encodedId}/`) ? preserved : `/obras/${encodedId}/resumen`);
        onNavigate?.();
    }

    return (
        <section className="relative mb-4 px-1">
            <p className="mb-1.5 px-1 text-[10px] font-black uppercase tracking-[0.16em] text-[var(--text-muted)]">
                Contexto
            </p>

            <button
                aria-expanded={open}
                aria-haspopup="listbox"
                className="flex w-full items-center gap-2.5 rounded-[var(--radius-md)] border border-emerald-200 bg-white px-3 py-2.5 text-left shadow-sm transition hover:border-emerald-300 focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
                onClick={() => setOpen((current) => !current)}
                type="button"
            >
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
                    {isObra ? <Building2 aria-hidden="true" size={16} /> : <Boxes aria-hidden="true" size={16} />}
                </span>

                <span className="min-w-0 flex-1">
                    <span className="block text-[10px] font-black uppercase tracking-[0.1em] text-emerald-700">
                        {isObra ? preset.unitLabel : "Portafolio"}
                    </span>
                    <span className="block truncate text-sm font-black text-[var(--text-primary)]">
                        {isObra ? (currentWork?.nombre || "Cargando…") : "Vista consolidada"}
                    </span>
                </span>

                <ChevronDown aria-hidden="true" className={`shrink-0 text-emerald-700 transition ${open ? "rotate-180" : ""}`} size={15} />
            </button>

            {open && (
                <div className="absolute left-1 right-1 top-full z-30 mt-1 max-h-72 overflow-y-auto rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl" role="listbox">
                    <button
                        aria-selected={!isObra}
                        className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs font-black transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 ${!isObra ? "bg-emerald-50 text-emerald-900" : "hover:bg-slate-50"}`}
                        onClick={selectPortfolio}
                        role="option"
                        type="button"
                    >
                        <Boxes aria-hidden="true" size={14} />
                        Portafolio
                        {!isObra && <Check aria-hidden="true" className="ml-auto" size={13} />}
                    </button>

                    {worksState.status === "loading" && (
                        <p className="flex items-center gap-2 px-3 py-2 text-xs text-[var(--text-muted)]">
                            <Loader2 aria-hidden="true" className="animate-spin" size={13} /> Cargando obras
                        </p>
                    )}

                    {worksState.status === "error" && (
                        <p className="px-3 py-2 text-xs text-rose-700">No se pudieron cargar las obras.</p>
                    )}

                    {worksState.rows.length > 0 && (
                        <p className="mt-1 px-3 pb-1 pt-2 text-[9px] font-black uppercase tracking-[0.14em] text-[var(--text-muted)]">
                            Obras
                        </p>
                    )}

                    {worksState.rows.map((work) => {
                        const id = routeId(work);
                        const selected = isObra && String(id) === String(scope.obraId);
                        const attention = ATTENTION_STATES.has(work.estado_ambiental);
                        return (
                            <button
                                aria-selected={selected}
                                className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs font-black transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 ${selected ? "bg-emerald-50 text-emerald-900" : "hover:bg-slate-50"}`}
                                key={id}
                                onClick={() => selectWork(work)}
                                onFocus={() => prefetchWork(activeOrganizacionId, id)}
                                onMouseEnter={() => prefetchWork(activeOrganizacionId, id)}
                                role="option"
                                type="button"
                            >
                                <Building2 aria-hidden="true" size={14} />
                                <span className="min-w-0 flex-1 truncate">{work.nombre || preset.unitLabel}</span>
                                <span aria-hidden="true" className={`h-1.5 w-1.5 shrink-0 rounded-full ${workAttentionDot(work)}`} title={attention ? "Requiere atención" : undefined} />
                                {selected && <Check aria-hidden="true" className="ml-1 shrink-0" size={13} />}
                            </button>
                        );
                    })}
                </div>
            )}
        </section>
    );
}


function OrganizationSelector({
    activeOrganizacionId,
    organizaciones,
    loadingOrganizaciones,
    presetKey,
    onChange,
}) {
    return (
        <section className="mb-3 px-2">
            <label
                className="sr-only"
                htmlFor="active-organization"
            >
                Organización activa
            </label>

            <div className="flex items-center gap-2">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--radius-md)] bg-[var(--bg-surface-subtle)] text-[var(--brand-primary)]">
                    <Building2
                        aria-hidden="true"
                        size={17}
                    />
                </span>

                <div className="min-w-0 flex-1">
                    <select
                        id="active-organization"
                        value={
                            activeOrganizacionId ||
                            ""
                        }
                        onChange={
                            onChange
                        }
                        className="w-full truncate border-0 bg-transparent p-0 text-sm font-black text-[var(--text-primary)] outline-none focus-visible:shadow-[var(--focus-ring)]"
                    >
                        <option value="">
                            Selecciona una organización
                        </option>

                        {organizaciones.map(
                            org => (
                                <option
                                    key={
                                        org.organizacion_id
                                    }
                                    value={
                                        org.organizacion_id
                                    }
                                >
                                    {org.nombre}
                                </option>
                            )
                        )}
                    </select>

                    <p className="truncate text-xs text-[var(--text-muted)]">
                        {getPresetLabel(
                            presetKey
                        )}
                    </p>
                </div>
            </div>

            {loadingOrganizaciones && (
                <p className="mt-1 pl-11 text-xs text-[var(--text-muted)]">
                    Actualizando organizaciones…
                </p>
            )}
        </section>
    );
}


function GeneralNavigation({
    navigation,
    expanded,
    setExpanded,
    exactPaths,
    onNavigate,
}) {
    return (
        <nav
            aria-label="Navegación principal"
            className="space-y-3"
        >
            <NavItem
                exact
                item={
                    navigation.home
                }
                onNavigate={
                    onNavigate
                }
            />

            {navigation.groups.map(
                group => (
                    <section
                        key={
                            group.id
                        }
                        aria-label={group.label || undefined}
                    >
                        {group.label && (
                            <p className="mb-1 px-2 text-[10px] font-black uppercase tracking-[0.15em] text-[var(--text-muted)]">
                                {group.label}
                            </p>
                        )}

                        <div className="space-y-0.5">
                            {group.items.map(
                                item =>
                                    item.children ? (
                                        <div
                                            key={
                                                item.id
                                            }
                                        >
                                            <button
                                                type="button"
                                                aria-expanded={Boolean(
                                                    expanded[
                                                    item.id
                                                    ]
                                                )}
                                                onClick={() =>
                                                    setExpanded(
                                                        current => ({
                                                            ...current,
                                                            [item.id]:
                                                                !current[
                                                                item.id
                                                                ],
                                                        })
                                                    )
                                                }
                                                className="flex w-full items-center gap-2.5 rounded-[var(--radius-md)] px-3 py-2 text-left text-sm font-bold text-[var(--text-secondary)] transition hover:bg-[var(--bg-surface-subtle)] hover:text-[var(--text-primary)]"
                                            >
                                                <item.icon
                                                    aria-hidden="true"
                                                    size={17}
                                                />

                                                <span className="min-w-0 flex-1 truncate">
                                                    {item.label}
                                                </span>

                                                <ChevronDown
                                                    aria-hidden="true"
                                                    size={15}
                                                    className={`transition ${expanded[
                                                        item.id
                                                    ]
                                                        ? "rotate-180"
                                                        : ""
                                                        }`}
                                                />
                                            </button>

                                            {expanded[
                                                item.id
                                            ] && (
                                                    <div className="ml-5 border-l border-[var(--sidebar-border)] pl-2">
                                                        {item.children.map(
                                                            child => (
                                                                <NavItem
                                                                    compact
                                                                    exact={exactPaths.has(
                                                                        child.path
                                                                    )}
                                                                    item={
                                                                        child
                                                                    }
                                                                    key={
                                                                        child.path
                                                                    }
                                                                    onNavigate={
                                                                        onNavigate
                                                                    }
                                                                />
                                                            )
                                                        )}
                                                    </div>
                                                )}
                                        </div>
                                    ) : (
                                        <NavItem
                                            exact={exactPaths.has(
                                                item.path
                                            )}
                                            item={
                                                item
                                            }
                                            key={
                                                item.path
                                            }
                                            onNavigate={
                                                onNavigate
                                            }
                                        />
                                    )
                            )}
                        </div>
                    </section>
                )
            )}
        </nav>
    );
}


function NavItem({
    compact = false,
    exact = false,
    item,
    onNavigate,
}) {
    const domain = getEnvironmentalDomain(item.domain);
    const Icon = domain?.icon || item.icon;

    return (
        <NavLink
            end={
                exact ||
                item.path ===
                "/inicio"
            }
            to={
                item.path
            }
            onClick={
                onNavigate
            }
            className={({
                isActive,
            }) =>
                `flex items-center gap-2.5 rounded-[var(--radius-md)] px-3 ${compact
                    ? "py-1.5 text-xs"
                    : "py-2 text-sm"
                } font-bold transition focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] ${isActive
                    ? domain ? `${domain.softBg} ${domain.text}` : "bg-[var(--sidebar-active)] text-[var(--brand-primary)]"
                    : "text-[var(--text-secondary)] hover:bg-[var(--bg-surface-subtle)] hover:text-[var(--text-primary)]"
                }`
            }
        >
            <Icon
                aria-hidden="true"
                className={domain?.text || ""}
                size={
                    compact
                        ? 15
                        : 17
                }
            />

            <span className="truncate">
                {item.label}
            </span>
        </NavLink>
    );
}

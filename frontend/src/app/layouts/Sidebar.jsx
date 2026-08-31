import {
    ArrowLeft,
    Building2,
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
    getNavigationForPreset,
    getWorkNavigation,
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
import { getWorkContext } from "@/features/obras/services/workspaceApi";
import { usePermissions } from "@/features/auth/hooks/usePermissions";
import { useOperationalWorkspace } from "@/features/workspace/context/OperationalWorkspaceContext";

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


    const navigation =
        useMemo(
            () => filterNavigation(getNavigationForPreset(preset), can),
            [can, preset]
        );


    const workNavigation =
        useMemo(
            () =>
                workId
                    ? filterNavigation(getWorkNavigation({
                        obraId: workId,
                        applicability: workApplicability.scope === applicabilityScope ? workApplicability.rows : [],
                    }), can)
                    : null,
            [applicabilityScope, can, workApplicability, workId]
        );


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

            {workNavigation ? (
                <WorkSidebar
                    navigation={workNavigation}
                    preset={preset}
                    workId={workId}
                    onNavigate={onNavigate}
                    onExit={returnToGeneralView}
                />
            ) : (
                <>
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
                </>
            )}
        </aside>
    );
}

function WorkSidebar({
    navigation,
    preset,
    workId,
    onNavigate,
    onExit,
}) {
    const navigate = useNavigate();
    const { pathname } = useLocation();
    const { activeOrganizacionId } = useOrganizacionActiva();
    const [selectorOpen, setSelectorOpen] = useState(false);
    const [worksState, setWorksState] = useState({ status: "loading", rows: [], error: "" });

    useEffect(() => {
        let active = true;
        setSelectorOpen(false);
        if (!activeOrganizacionId) {
            setWorksState({ status: "ready", rows: [], error: "" });
            return () => { active = false; };
        }
        setWorksState({ status: "loading", rows: [], error: "" });
        getOrganizacionObras(activeOrganizacionId)
            .then((data) => {
                if (active) setWorksState({ status: "ready", rows: Array.isArray(data) ? data : data?.results || [], error: "" });
            })
            .catch(() => {
                if (active) setWorksState({ status: "error", rows: [], error: "No se pudieron cargar las obras." });
            });
        return () => { active = false; };
    }, [activeOrganizacionId]);

    const routeId = (work) => work.id || work.obra_id || work.codigo_obra;
    const currentWork = worksState.rows.find((work) => String(routeId(work)) === String(workId));
    const canSwitch = worksState.status === "ready" && worksState.rows.length > 1;

    function selectWork(nextWork) {
        const nextId = routeId(nextWork);
        if (!nextId || String(nextId) === String(workId)) {
            setSelectorOpen(false);
            return;
        }
        const encodedId = encodeURIComponent(nextId);
        const preserved = pathname.replace(/^\/obras\/[^/]+/, `/obras/${encodedId}`);
        navigate(preserved.startsWith(`/obras/${encodedId}/`) ? preserved : `/obras/${encodedId}/resumen`);
        setSelectorOpen(false);
        onNavigate?.();
    }

    return (
        <>
            <button
                type="button"
                onClick={onExit}
                className="
                    mb-5 flex items-center gap-2
                    rounded-[var(--radius-md)]
                    border border-emerald-200/80
                    bg-white
                    px-3 py-2.5
                    text-sm font-black
                    text-[var(--brand-primary)]
                    shadow-sm
                    transition
                    hover:border-emerald-300
                    hover:bg-emerald-50
                    focus-visible:outline-none
                    focus-visible:shadow-[var(--focus-ring)]
                "
            >
                <navigation.exit.icon
                    aria-hidden="true"
                    size={17}
                />

                Volver a visión general
            </button>

            <div className="relative mb-5 px-1">
                <p className="text-[10px] font-black uppercase tracking-[0.16em] text-emerald-700">
                    Obra activa
                </p>
                {worksState.status === "loading" ? <div className="mt-2 flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-3 text-xs text-[var(--text-muted)]"><Loader2 aria-hidden="true" size={15} className="animate-spin" />Cargando obra</div> : worksState.status === "error" ? <div className="mt-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">{worksState.error}</div> : !currentWork ? <div className="mt-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">Obra no disponible</div> : <>
                    <button type="button" disabled={!canSwitch} aria-expanded={canSwitch ? selectorOpen : undefined} aria-haspopup={canSwitch ? "listbox" : undefined} onClick={() => canSwitch && setSelectorOpen((open) => !open)} className="mt-2 flex w-full items-center gap-2 rounded-xl border border-emerald-200 bg-white px-3 py-2.5 text-left shadow-sm transition hover:border-emerald-300 focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)] disabled:cursor-default">
                        <Building2 aria-hidden="true" size={17} className="shrink-0 text-emerald-700" />
                        <span className="min-w-0 flex-1"><span className="block truncate text-sm font-black text-[var(--text-primary)]">{currentWork.nombre || preset.unitLabel}</span></span>
                        {canSwitch && <ChevronDown aria-hidden="true" size={15} className={`shrink-0 text-emerald-700 transition ${selectorOpen ? "rotate-180" : ""}`} />}
                    </button>
                    {selectorOpen && <div role="listbox" aria-label="Seleccionar obra" className="absolute left-1 right-1 top-full z-30 mt-1 max-h-64 overflow-y-auto rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl">{worksState.rows.map((work) => { const id = routeId(work); const selected = String(id) === String(workId); return <button key={id} type="button" role="option" aria-selected={selected} onClick={() => selectWork(work)} className={`w-full rounded-lg px-3 py-2 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 ${selected ? "bg-emerald-50 text-emerald-900" : "hover:bg-slate-50"}`}><span className="block truncate text-xs font-black">{work.nombre || preset.unitLabel}</span></button>; })}</div>}
                </>}
            </div>

            <nav
                aria-label="Navegación de obra"
                className="min-h-0 flex-1 space-y-4 overflow-y-auto px-1 pb-2"
            >
                {navigation.groups.map(group => (
                    <section
                        key={group.id}
                        aria-labelledby={`work-nav-${group.id}`}
                    >
                        <p
                            id={`work-nav-${group.id}`}
                            className="
                                mb-1
                                px-2
                                text-[10px]
                                font-black
                                uppercase
                                tracking-[0.15em]
                                text-[var(--text-muted)]
                            "
                        >
                            {group.label}
                        </p>

                        <div className="space-y-0.5">
                            {group.items.map(item => (
                                <NavItem
                                    exact
                                    item={item}
                                    key={item.path}
                                    onNavigate={onNavigate}
                                />
                            ))}
                        </div>
                    </section>
                ))}
            </nav>
        </>
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
        <section className="mb-4 px-2">
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
            className="min-h-0 flex-1 space-y-3 overflow-y-auto px-1 pb-2"
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
                        aria-labelledby={`nav-${group.id}`}
                    >
                        <p
                            id={`nav-${group.id}`}
                            className="mb-1 px-2 text-[10px] font-black uppercase tracking-[0.15em] text-[var(--text-muted)]"
                        >
                            {group.label}
                        </p>

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

import {
    Building2,
    ChevronDown,
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


    const navigation =
        useMemo(
            () =>
                getNavigationForPreset(
                    preset
                ),
            [preset]
        );


    const workNavigation =
        useMemo(
            () =>
                workId
                    ? getWorkNavigation({
                        obraId: workId,
                    })
                    : null,
            [workId]
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


    return (
        <aside className="flex min-h-full w-full shrink-0 flex-col border-b border-[var(--sidebar-border)] bg-[var(--sidebar)] px-3 py-4 text-[var(--text-main)] shadow-[18px_0_50px_rgba(19,34,56,0.05)] lg:sticky lg:top-[72px] lg:h-[calc(100vh-72px)] lg:w-64 lg:border-b-0 lg:border-r">

            {workNavigation ? (
                <WorkSidebar
                    navigation={workNavigation}
                    preset={preset}
                    onNavigate={onNavigate}
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
    onNavigate,
}) {
    return (
        <>
            <NavLink
                to={navigation.exit.path}
                onClick={onNavigate}
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
            </NavLink>

            <div className="mb-5 px-2">
                <p className="text-[10px] font-black uppercase tracking-[0.16em] text-emerald-700">
                    {preset.unitLabel}
                </p>

                <p className="mt-1 text-sm font-black text-[var(--text-primary)]">
                    Navegación de la obra
                </p>

                <p className="mt-1 text-xs leading-5 text-[var(--text-muted)]">
                    Estás trabajando únicamente con la información de esta {preset.unitLabel.toLowerCase()}.
                </p>
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
    const Icon =
        item.icon;

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
                    ? "bg-[var(--sidebar-active)] text-[var(--brand-primary)]"
                    : "text-[var(--text-secondary)] hover:bg-[var(--bg-surface-subtle)] hover:text-[var(--text-primary)]"
                }`
            }
        >
            <Icon
                aria-hidden="true"
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
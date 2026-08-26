import { getEnvironmentalDomain } from "@/shared/config/environmentalDomains";

export default function EnvironmentalFlowHero({
  domainKey,
  title,
  description,
  badges = [],
  stats = [],
  primaryAction,
  secondaryAction,
}) {
  const identity =
    getEnvironmentalDomain(
      domainKey,
    );

  const Icon =
    identity?.icon;

  return (
    <section
      className={`
        relative overflow-hidden
        rounded-[28px] border
        ${identity?.border || "border-[var(--border-subtle)]"}
        bg-gradient-to-br
        ${identity?.accent || "from-white via-emerald-50/60 to-white"}
        p-6
        shadow-[0_16px_42px_rgba(15,23,42,0.07)]
        sm:p-7
      `}
    >
      <div
        aria-hidden="true"
        className={`
          absolute -right-16 -top-20
          h-56 w-56 rounded-full
          opacity-60 blur-3xl
          ${identity?.softBg || "bg-emerald-50"}
        `}
      />

      <div className="relative space-y-6">
        <div className="
          flex flex-col gap-6
          lg:flex-row
          lg:items-center
          lg:justify-between
        ">
          <div className="
            flex min-w-0
            items-start gap-4
            sm:gap-5
          ">
            {Icon && (
              <span
                className={`
                  flex h-14 w-14
                  shrink-0 items-center
                  justify-center rounded-2xl
                  bg-white/85 shadow-sm
                  ring-1 ring-current/10
                  ${identity?.text || "text-emerald-700"}
                `}
              >
                <Icon
                  aria-hidden="true"
                  size={27}
                />
              </span>
            )}

            <div className="min-w-0">
              <p
                className={`
                  text-xs font-black uppercase
                  tracking-[0.16em]
                  ${identity?.text || "text-emerald-700"}
                `}
              >
                Flujo ambiental
              </p>

              <h1 className="
                mt-1 text-2xl
                font-black tracking-tight
                text-[var(--text-primary)]
                sm:text-3xl
              ">
                {title}
              </h1>

              <p className="
                mt-2 max-w-2xl
                text-sm leading-6
                text-[var(--text-secondary)]
                sm:text-base
              ">
                {description}
              </p>

              {badges.length > 0 && (
                <div className="
                  mt-4 flex
                  flex-wrap gap-2
                ">
                  {badges.map(
                    (badge) => (
                      <span
                        key={badge}
                        className="
                          inline-flex min-h-7
                          items-center rounded-full
                          border border-white/80
                          bg-white/75 px-3
                          text-xs font-bold
                          text-[var(--text-secondary)]
                          shadow-sm
                          backdrop-blur-sm
                        "
                      >
                        {badge}
                      </span>
                    ),
                  )}
                </div>
              )}
            </div>
          </div>

          {(primaryAction ||
            secondaryAction) && (
              <div className="
              flex shrink-0
              flex-wrap items-center
              gap-2
              lg:max-w-[28rem]
              lg:justify-end
            ">
                {primaryAction}
                {secondaryAction}
              </div>
            )}
        </div>

        {stats.length > 0 && (
          <div className="
            grid gap-3
            border-t border-black/5
            pt-5
            sm:grid-cols-2
            xl:grid-cols-4
          ">
            {stats.map(
              (stat) => (
                <div
                  key={stat.label}
                  className="
                    rounded-2xl
                    border border-white/80
                    bg-white/65
                    px-4 py-3
                    shadow-sm
                    backdrop-blur-sm
                  "
                >
                  <p className="
                    text-[11px]
                    font-black uppercase
                    tracking-[0.12em]
                    text-[var(--text-muted)]
                  ">
                    {stat.label}
                  </p>

                  <p className="
                    mt-1 truncate
                    text-sm font-black
                    text-[var(--text-primary)]
                  ">
                    {stat.value}
                  </p>
                </div>
              ),
            )}
          </div>
        )}
      </div>
    </section>
  );
}
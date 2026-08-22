import {
    SectionHeader,
} from "@/shared/ui";
import { getEnvironmentalDomain } from "@/shared/config/environmentalDomains";

export default function OperationDomainShell({
    title,
    description,
    domainKey,
    applicability,
    action,
    alerts,
    metrics,
    children,
}) {
    const identity = getEnvironmentalDomain(domainKey);
    const Icon = identity?.icon;

    return (
        <div className="space-y-6">
            <section
                className={`
          rounded-[24px]
          border
          ${identity?.border || "border-[var(--border-subtle)]"}
          bg-gradient-to-br
          ${identity?.accent || "from-white via-emerald-50/70 to-white"}
          p-5
          shadow-[0_10px_30px_rgba(15,23,42,0.04)]
        `}
            >
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="flex items-start gap-4">
                    {Icon && <span className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl ring-1 ring-current/10 ${identity.softBg} ${identity.text}`}><Icon aria-hidden="true" size={23} /></span>}
                    <SectionHeader eyebrow="OPERACIÓN" title={title} description={description} />
                  </div>
                  {action && <div className="shrink-0">{action}</div>}
                </div>

                {applicability && (
                    <div className="mt-5">
                        {applicability}
                    </div>
                )}
            </section>

            {alerts}

            {metrics}

            {children}
        </div>
    );
}

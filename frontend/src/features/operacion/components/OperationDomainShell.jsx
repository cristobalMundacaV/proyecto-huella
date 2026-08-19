import {
    SectionHeader,
} from "@/shared/ui";

export default function OperationDomainShell({
    title,
    description,
    applicability,
    alerts,
    metrics,
    children,
}) {
    return (
        <div className="space-y-6">
            <section
                className="
          rounded-[24px]
          border
          border-[var(--border-subtle)]
          bg-[linear-gradient(135deg,rgba(255,255,255,1),rgba(236,253,245,0.72))]
          p-5
          shadow-[0_10px_30px_rgba(15,23,42,0.04)]
        "
            >
                <SectionHeader
                    eyebrow="OPERACIÓN"
                    title={title}
                    description={description}
                />

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
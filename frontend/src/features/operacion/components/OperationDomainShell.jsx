import { SectionHeader } from "@/shared/ui";

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
            <section>
                <SectionHeader
                    eyebrow="OPERACIÓN"
                    title={title}
                    description={description}
                />

                {applicability && (
                    <div className="mt-4">
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
import EnvironmentalFlowHero from "./EnvironmentalFlowHero";
import FlowWorkspaceNav from "./FlowWorkspaceNav";

export default function OperationDomainShell({
  title,
  description,
  domainKey,
  badges,
  heroStats,
  primaryAction,
  secondaryAction,
  alerts,
  metrics,
  children,
}) {
  return (
    <div className="space-y-6">
      <EnvironmentalFlowHero
        domainKey={domainKey}
        title={title}
        description={description}
        badges={badges}
        stats={heroStats}
        primaryAction={primaryAction}
        secondaryAction={secondaryAction}
      />

      <FlowWorkspaceNav />

      {alerts}
      {metrics}
      {children}
    </div>
  );
}

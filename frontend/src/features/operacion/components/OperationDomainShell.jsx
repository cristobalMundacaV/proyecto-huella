import EnvironmentalFlowHero from "./EnvironmentalFlowHero";

export default function OperationDomainShell({ title, description, domainKey, badges, primaryAction, secondaryAction, alerts, metrics, children }) {
  return (
    <div className="space-y-6">
      <EnvironmentalFlowHero domainKey={domainKey} title={title} description={description} badges={badges} primaryAction={primaryAction} secondaryAction={secondaryAction} />
      {alerts}
      {metrics}
      {children}
    </div>
  );
}

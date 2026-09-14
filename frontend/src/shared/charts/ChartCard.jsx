import { Card, CardContent } from "../ui/Card";
import { SectionHeader } from "../ui/Headers";
import { EmptyState, LoadingState } from "../ui/Feedback";

export default function ChartCard({ title, description, children, loading = false, empty = false, action }) {
  return <Card className="h-full"><CardContent className="flex h-full flex-col">
    <SectionHeader title={title} description={description} action={action} />
    {loading ? <LoadingState /> : empty ? <ChartEmptyState /> : children}
  </CardContent></Card>;
}

export function ChartEmptyState() {
  return <EmptyState className="min-h-0 flex-1" title="Sin datos para graficar" description="El gráfico aparecerá cuando existan datos para este alcance." />;
}

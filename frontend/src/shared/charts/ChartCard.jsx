import {Card,CardContent}from"../ui/Card";import {SectionHeader}from"../ui/Headers";import{EmptyState,LoadingState}from"../ui/Feedback";
export default function ChartCard({title,description,children,loading=false,empty=false,action}){return <Card><CardContent><SectionHeader title={title} description={description} action={action}/>{loading?<LoadingState/>:empty?<ChartEmptyState/>:children}</CardContent></Card>}
export function ChartEmptyState(){return <EmptyState title="Sin datos para graficar" description="El gráfico aparecerá cuando existan datos para este alcance."/>}

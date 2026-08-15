import {Link2}from"lucide-react";import {Button}from"./Button";
export default function TraceabilityLink({onClick,label="Ver origen"}){return <Button variant="ghost" size="sm" leftIcon={Link2} onClick={onClick}>{label}</Button>}

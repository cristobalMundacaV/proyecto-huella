import { Link } from "react-router-dom";
import { Button } from "@/shared/ui/Button";
import { Card, CardContent } from "@/shared/ui/Card";

export default function NotFoundPage({ authenticated = false }) {
  return <main className={authenticated ? "py-16" : "flex min-h-screen items-center justify-center bg-[var(--bg-app)] p-6"}>
    <Card className="mx-auto max-w-lg text-center"><CardContent className="p-8"><p className="text-sm font-black uppercase tracking-widest text-[var(--brand-primary)]">404</p><h1 className="mt-2 text-3xl font-black">Página no encontrada</h1><p className="mt-3 text-[var(--text-muted)]">La ruta solicitada no existe en Carbono Zero.</p><Link to={authenticated ? "/inicio" : "/"}><Button className="mt-6">Volver al inicio</Button></Link></CardContent></Card>
  </main>;
}

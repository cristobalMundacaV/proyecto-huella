import { Link } from "react-router-dom";

export default function NotFoundPage({ authenticated = false }) {
  return <main className={authenticated ? "py-16 text-center" : "flex min-h-screen items-center justify-center bg-slate-950 p-6 text-white"}>
    <section>
      <p className="text-sm font-black uppercase tracking-widest text-emerald-600">404</p>
      <h1 className="mt-2 text-3xl font-black">Página no encontrada</h1>
      <p className="mt-3 text-slate-500">La ruta solicitada no existe en Carbono Zero.</p>
      <Link to={authenticated ? "/inicio" : "/"} className="mt-6 inline-block rounded-xl bg-emerald-700 px-5 py-3 font-bold text-white">Volver al inicio</Link>
    </section>
  </main>;
}

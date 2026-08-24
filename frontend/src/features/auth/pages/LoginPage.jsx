import { useState } from "react";
import { Leaf, Lock, Mail } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "@/features/auth/context/AuthContext";
import { Button } from "@/shared/ui/Button";

const initialForm = {
  password: "",
  email: "",
  first_name: "",
  last_name: "",
};

function LoginPage() {
  const { bootstrap, enterDemo, hasUsers, login } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [form, setForm] = useState(initialForm);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const isBootstrap = !hasUsers;

  const updateForm = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
    setError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      if (isBootstrap) {
        await bootstrap(form);
      } else {
        await login({ email: form.email, password: form.password });
      }
      navigate(location.state?.returnTo || "/inicio", { replace: true });
    } catch (requestError) {
      setError(
        requestError.response?.data?.error ||
          "No se pudo iniciar sesion. Revisa tus datos."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <main
      className="min-h-screen bg-slate-950 bg-cover bg-center text-slate-100"
      style={{ backgroundImage: "url('/carbono-zero-fondo.png')" }}
    >
      <div className="min-h-screen bg-gradient-to-r from-slate-950/10 via-slate-950/25 to-slate-950/85">
        <section className="mx-auto flex min-h-screen max-w-7xl items-center justify-end px-4 py-8 sm:px-8">
          <form
            onSubmit={handleSubmit}
            className="w-full max-w-md rounded-3xl border border-emerald-300/20 bg-slate-950/80 p-6 shadow-2xl shadow-emerald-950/40 backdrop-blur-xl sm:p-8"
          >
            <div className="mb-8">
              <div className="mb-5 inline-flex rounded-2xl border border-emerald-300/20 bg-emerald-300/10 p-3 text-emerald-200">
                <Leaf size={24} />
              </div>
              <p className="text-xs font-bold uppercase tracking-[0.25em] text-emerald-200">
                Carbono Zero
              </p>
              <h1 className="mt-3 text-3xl font-black text-white">
                {isBootstrap ? "Crea el primer administrador" : "Inicia sesion"}
              </h1>
              <p className="mt-3 text-sm leading-6 text-slate-300">
                {isBootstrap
                  ? "Aun no hay usuarios en el sistema. Crea una cuenta inicial para administrar organizaciones y usuarios."
                  : "Accede a tu organización para gestionar información, indicadores, problemáticas y trazabilidad ambiental."}
              </p>
            </div>

            {isBootstrap && (
              <div className="grid gap-4 sm:grid-cols-2">
                <Field
                  label="Nombre"
                  name="first_name"
                  onChange={updateForm}
                  value={form.first_name}
                />
                <Field
                  label="Apellido"
                  name="last_name"
                  onChange={updateForm}
                  value={form.last_name}
                />
              </div>
            )}

            <div className="mt-4 space-y-4">
              <Field
                icon={<Mail size={18} />}
                label="Correo electrónico"
                name="email"
                onChange={updateForm}
                placeholder="nombre@empresa.cl"
                required
                value={form.email}
              />
              <Field
                icon={<Lock size={18} />}
                label="Clave"
                name="password"
                onChange={updateForm}
                required
                type="password"
                value={form.password}
              />
            </div>

            {error && (
              <p className="mt-4 rounded-2xl border border-rose-400/20 bg-rose-400/10 p-3 text-sm text-rose-100">
                {error}
              </p>
            )}

            {!isBootstrap && <Link to="/recuperar-contrasena" className="block text-right text-sm font-bold text-emerald-200 hover:text-white">¿Olvidaste tu contraseña?</Link>}

            <Button
              type="submit"
              disabled={loading}
              loading={loading}
              className="mt-6 w-full"
            >
              {loading
                ? "Procesando..."
                : isBootstrap
                  ? "Crear administrador"
                  : "Entrar al sistema"}
            </Button>

            <Button
              onClick={() => { enterDemo(); navigate("/inicio", { replace: true }); }}
              variant="secondary"
              className="mt-3 w-full"
            >
              Ver demo
            </Button>

            <p className="mt-3 text-center text-xs leading-5 text-slate-500">
              El modo demo permite ver la informacion sin crear, editar ni eliminar datos.
            </p>
          </form>
        </section>
      </div>
    </main>
  );
}

function Field({ icon, label, name, onChange, placeholder, required = false, type = "text", value }) {
  return (
    <label className="block">
      <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
        {label}
      </span>
      <div className="mt-2 flex items-center gap-3 rounded-2xl border border-slate-700 bg-slate-950/80 px-4 py-3 text-slate-100 transition focus-within:border-emerald-300/60">
        {icon && <span className="text-emerald-200">{icon}</span>}
        <input
          name={name}
          onChange={onChange}
          required={required}
          placeholder={placeholder}
          type={type}
          value={value}
          className="w-full bg-transparent text-sm outline-none placeholder:text-slate-600"
        />
      </div>
    </label>
  );
}

export default LoginPage;

import { useState } from "react";
import { KeyRound } from "lucide-react";
import { Button, Input } from "@/shared/ui";
import Toast from "@/shared/components/Toast";
import { changePassword } from "../services/onboardingApi";

export default function SecurityPage() {
  const [form, setForm] = useState({ current_password: "", password: "", confirmation: "" }); const [saving, setSaving] = useState(false); const [toast, setToast] = useState(null);
  const submit = async (event) => { event.preventDefault(); setSaving(true); setToast({ id: Date.now(), loading: true, message: "Actualizando contraseña", subtitle: "Estamos protegiendo los cambios de tu cuenta." }); try { const result = await changePassword(form); setForm({ current_password: "", password: "", confirmation: "" }); setToast({ id: Date.now(), message: "Contraseña actualizada", subtitle: result.detail }); } catch (error) { const data = error.response?.data; setToast({ id: Date.now(), tone: "error", message: "No pudimos cambiar la contraseña", subtitle: data?.current_password?.[0] || data?.password?.[0] || data?.confirmation?.[0] || data?.detail || "Revisa los datos e inténtalo nuevamente." }); } finally { setSaving(false); } };
  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value });
  return <main className="mx-auto max-w-2xl space-y-6"><Toast {...toast} toastKey={toast?.id} onClose={() => setToast(null)} /><header><span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-800"><KeyRound /></span><h1 className="mt-4 text-3xl font-black">Seguridad de tu cuenta</h1><p className="mt-2 text-sm text-slate-600">Cambia tu contraseña sin cerrar la sesión actual.</p></header><form onSubmit={submit} className="space-y-4 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"><Input label="Contraseña actual" type="password" required value={form.current_password} onChange={set("current_password")} /><Input label="Nueva contraseña" type="password" required helper="Usa al menos 8 caracteres y evita contraseñas comunes." value={form.password} onChange={set("password")} /><Input label="Confirmar nueva contraseña" type="password" required value={form.confirmation} onChange={set("confirmation")} /><Button type="submit" loading={saving} className="w-full">Guardar nueva contraseña</Button></form></main>;
}

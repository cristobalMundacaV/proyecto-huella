import { api } from "@/shared/services/api";
export const getOnboarding = async (organizationId) => (await api.get("/onboarding/", { headers: { "X-Organization-ID": organizationId } })).data;
export const saveOnboardingStep = async (organizationId, step, data) => (await api.patch("/onboarding/", { step, data }, { headers: { "X-Organization-ID": organizationId } })).data;
export const activateAccount = async (uid, token, payload) => (await api.post(`/auth/activar/${uid}/${token}/`, payload)).data;
export const requestPasswordReset = async (email) => (await api.post("/auth/password-reset/", { email })).data;
export const confirmPasswordReset = async (uid, token, payload) => (await api.post(`/auth/password-reset/${uid}/${token}/`, payload)).data;
export const changePassword = async (payload) => (await api.post("/auth/cambiar-contrasena/", payload)).data;

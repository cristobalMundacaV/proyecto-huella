import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api",
});

export async function uploadDataFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post("/upload/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return response.data;
}

export async function compareScenarioFiles(datasetActual, datasetSimulado) {
  const formData = new FormData();
  formData.append("dataset_actual", datasetActual);
  formData.append("dataset_simulado", datasetSimulado);

  const response = await api.post("/compare/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return response.data;
}

export async function getAiAdvisor(payload) {
  const response = await api.post("/ai-advisor/", payload);
  return response.data;
}

export async function simulateScenario(payload) {
  const response = await api.post("/simulate/", payload);
  return response.data;
}

export async function optimizeScenarioApi(rows) {
  const response = await api.post("/optimize/", { rows });
  return response.data;
}

export async function getRiskScore(payload) {
  const response = await api.post("/risk-score/", payload);
  return response.data;
}

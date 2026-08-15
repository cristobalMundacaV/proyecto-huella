export const label = (value) => value === null || value === undefined || value === "" ? "Sin datos" : String(value).replaceAll("_", " ");
export const problemTone = (state) => ["cerrada", "resuelta"].includes(state) ? "success" : ["escalada", "escalada_profesional", "no_resuelta"].includes(state) ? "danger" : ["implementando", "seguimiento", "evaluando"].includes(state) ? "info" : "warning";
export const currentAction = (actions = []) => actions.find((action) => ["seleccionada", "en_implementacion", "seguimiento"].includes(action.estado));
export const currentCycle = (cycles = []) => cycles.length ? [...cycles].sort((a, b) => b.numero - a.numero)[0] : null;

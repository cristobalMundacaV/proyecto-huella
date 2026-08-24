const RAW_CHILE_REGIONS = [
  {
    region: "Arica y Parinacota",
    comunas: ["Arica", "Camarones", "Putre", "General Lagos"],
  },
  {
    region: "Tarapacá",
    comunas: ["Iquique", "Alto Hospicio", "Pozo Almonte", "Camiña", "Colchane", "Huara", "Pica"],
  },
  {
    region: "Antofagasta",
    comunas: ["Antofagasta", "Mejillones", "Sierra Gorda", "Taltal", "Calama", "Ollagí¼e", "San Pedro de Atacama", "Tocopilla", "Marí­a Elena"],
  },
  {
    region: "Atacama",
    comunas: ["Copiapó", "Caldera", "Tierra Amarilla", "Chañaral", "Diego de Almagro", "Vallenar", "Alto del Carmen", "Freirina", "Huasco"],
  },
  {
    region: "Coquimbo",
    comunas: ["La Serena", "Coquimbo", "Andacollo", "La Higuera", "Paiguano", "Vicuña", "Illapel", "Canela", "Los Vilos", "Salamanca", "Ovalle", "Combarbalá", "Monte Patria", "Punitaqui", "Rí­o Hurtado"],
  },
  {
    region: "Valparaí­so",
    comunas: ["Valparaí­so", "Casablanca", "Concón", "Juan Fernández", "Puchuncaví­", "Quintero", "Viña del Mar", "Isla de Pascua", "Los Andes", "Calle Larga", "Rinconada", "San Esteban", "La Ligua", "Cabildo", "Papudo", "Petorca", "Zapallar", "Quillota", "Calera", "Hijuelas", "La Cruz", "Nogales", "San Antonio", "Algarrobo", "Cartagena", "El Quisco", "El Tabo", "Santo Domingo", "San Felipe", "Catemu", "Llaillay", "Panquehue", "Putaendo", "Santa Marí­a", "Quilpué", "Limache", "Olmué", "Villa Alemana"],
  },
  {
    region: "Región del Libertador Gral. Bernardo O'Higgins",
    comunas: ["Rancagua", "Codegua", "Coinco", "Coltauco", "Doñihue", "Graneros", "Las Cabras", "Machalí­", "Malloa", "Mostazal", "Olivar", "Peumo", "Pichidegua", "Quinta de Tilcoco", "Rengo", "Requí­noa", "San Vicente", "Pichilemu", "La Estrella", "Litueche", "Marchihue", "Navidad", "Paredones", "San Fernando", "Chépica", "Chimbarongo", "Lolol", "Nancagua", "Palmilla", "Peralillo", "Placilla", "Pumanque", "Santa Cruz"],
  },
  {
    region: "Región del Maule",
    comunas: ["Talca", "Constitución", "Curepto", "Empedrado", "Maule", "Pelarco", "Pencahue", "Rí­o Claro", "San Clemente", "San Rafael", "Cauquenes", "Chanco", "Pelluhue", "Curicó", "Hualañé", "Licantén", "Molina", "Rauco", "Romeral", "Sagrada Familia", "Teno", "Vichuquén", "Linares", "Colbún", "Longaví­", "Parral", "Retiro", "San Javier", "Villa Alegre", "Yerbas Buenas"],
  },
  {
    region: "Región de í‘uble",
    comunas: ["Cobquecura", "Coelemu", "Ninhue", "Portezuelo", "Quirihue", "Ránquil", "Treguaco", "Bulnes", "Chillán Viejo", "Chillán", "El Carmen", "Pemuco", "Pinto", "Quillón", "San Ignacio", "Yungay", "Coihueco", "í‘iquén", "San Carlos", "San Fabián", "San Nicolás"],
  },
  {
    region: "Región del Biobí­o",
    comunas: ["Concepción", "Coronel", "Chiguayante", "Florida", "Hualqui", "Lota", "Penco", "San Pedro de la Paz", "Santa Juana", "Talcahuano", "Tomé", "Hualpén", "Lebu", "Arauco", "Cañete", "Contulmo", "Curanilahue", "Los ílamos", "Tirúa", "Los íngeles", "Antuco", "Cabrero", "Laja", "Mulchén", "Nacimiento", "Negrete", "Quilaco", "Quilleco", "San Rosendo", "Santa Bárbara", "Tucapel", "Yumbel", "Alto Biobí­o"],
  },
  {
    region: "Región de la Araucaní­a",
    comunas: ["Temuco", "Carahue", "Cunco", "Curarrehue", "Freire", "Galvarino", "Gorbea", "Lautaro", "Loncoche", "Melipeuco", "Nueva Imperial", "Padre las Casas", "Perquenco", "Pitrufquén", "Pucón", "Saavedra", "Teodoro Schmidt", "Toltén", "Vilcún", "Villarrica", "Cholchol", "Angol", "Collipulli", "Curacautí­n", "Ercilla", "Lonquimay", "Los Sauces", "Lumaco", "Purén", "Renaico", "Traiguén", "Victoria"],
  },
  {
    region: "Región de Los Rí­os",
    comunas: ["Valdivia", "Corral", "Lanco", "Los Lagos", "Máfil", "Mariquina", "Paillaco", "Panguipulli", "La Unión", "Futrono", "Lago Ranco", "Rí­o Bueno"],
  },
  {
    region: "Región de Los Lagos",
    comunas: ["Puerto Montt", "Calbuco", "Cochamó", "Fresia", "Frutillar", "Los Muermos", "Llanquihue", "Maullí­n", "Puerto Varas", "Castro", "Ancud", "Chonchi", "Curaco de Vélez", "Dalcahue", "Puqueldón", "Queilén", "Quellón", "Quemchi", "Quinchao", "Osorno", "Puerto Octay", "Purranque", "Puyehue", "Rí­o Negro", "San Juan de la Costa", "San Pablo", "Chaitén", "Futaleufú", "Hualaihué", "Palena"],
  },
  {
    region: "Región Aisén del Gral. Carlos Ibáñez del Campo",
    comunas: ["Coihaique", "Lago Verde", "Aisén", "Cisnes", "Guaitecas", "Cochrane", "O'Higgins", "Tortel", "Chile Chico", "Rí­o Ibáñez"],
  },
  {
    region: "Región de Magallanes y de la Antártica Chilena",
    comunas: ["Punta Arenas", "Laguna Blanca", "Rí­o Verde", "San Gregorio", "Cabo de Hornos (Ex Navarino)", "Antártica", "Porvenir", "Primavera", "Timaukel", "Natales", "Torres del Paine"],
  },
  {
    region: "Región Metropolitana de Santiago",
    comunas: ["Cerrillos", "Cerro Navia", "Conchalí­", "El Bosque", "Estación Central", "Huechuraba", "Independencia", "La Cisterna", "La Florida", "La Granja", "La Pintana", "La Reina", "Las Condes", "Lo Barnechea", "Lo Espejo", "Lo Prado", "Macul", "Maipú", "í‘uñoa", "Pedro Aguirre Cerda", "Peñalolén", "Providencia", "Pudahuel", "Quilicura", "Quinta Normal", "Recoleta", "Renca", "Santiago", "San Joaquí­n", "San Miguel", "San Ramón", "Vitacura", "Puente Alto", "Pirque", "San José de Maipo", "Colina", "Lampa", "Tiltil", "San Bernardo", "Buin", "Calera de Tango", "Paine", "Melipilla", "Alhué", "Curacaví­", "Marí­a Pinto", "San Pedro", "Talagante", "El Monte", "Isla de Maipo", "Padre Hurtado", "Peñaflor"],
  },
];

const REGION_IDENTITIES = [
  ["15", "Región de Arica y Parinacota", 0], ["01", "Región de Tarapacá", 1], ["02", "Región de Antofagasta", 2], ["03", "Región de Atacama", 3], ["04", "Región de Coquimbo", 4], ["05", "Región de Valparaíso", 5], ["13", "Región Metropolitana de Santiago", 15], ["06", "Región del Libertador General Bernardo O’Higgins", 6], ["07", "Región del Maule", 7], ["16", "Región de Ñuble", 8], ["08", "Región del Biobío", 9], ["09", "Región de La Araucanía", 10], ["14", "Región de Los Ríos", 11], ["10", "Región de Los Lagos", 12], ["11", "Región de Aysén del General Carlos Ibáñez del Campo", 13], ["12", "Región de Magallanes y de la Antártica Chilena", 14],
];
const SPELLING = { Paiguano: "Paihuano", Calera: "La Calera", Llaillay: "Llay-Llay", Treguaco: "Trehuaco", "Padre las Casas": "Padre Las Casas", Coihaique: "Coyhaique", Aisén: "Aysén" };
const repair = (value) => String(value).replaceAll("í­", "í").replaceAll("í‘", "Ñ").replaceAll("í", "Á").replaceAll("í¼", "ü");

export const CHILE_REGIONS = REGION_IDENTITIES.map(([codigo, nombre, rawIndex]) => ({ codigo, nombre, region: nombre, comunas: RAW_CHILE_REGIONS[rawIndex].comunas.map((rawName, index) => { const repaired = repair(rawName); return { codigo: `${codigo}-${String(index + 1).padStart(3, "0")}`, nombre: SPELLING[repaired] || repaired }; }) }));
export const CHILE_REGION_NAMES = CHILE_REGIONS.map((item) => item.nombre);

export function getComunasByRegion(region) {
  return CHILE_REGIONS.find((item) => item.nombre === region || item.codigo === region)?.comunas || [];
}

export function isValidChileLocation(region, comuna) { return getComunasByRegion(region).some((item) => item.nombre === comuna || item.codigo === comuna); }
export function selectChileRegion(region) { return { region, comuna: "" }; }

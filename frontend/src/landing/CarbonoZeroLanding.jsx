import { useEffect, useMemo, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import {
  ArrowRight,
  BarChart3,
  Building2,
  Check,
  ChevronRight,
  CircleGauge,
  CloudCog,
  Database,
  Factory,
  FileCheck2,
  Gauge,
  Globe2,
  Leaf,
  Menu,
  MessageCircle,
  RadioTower,
  Recycle,
  Route,
  SearchCheck,
  ShieldCheck,
  Sparkles,
  Trees,
  Truck,
  WandSparkles,
  Waves,
  X,
  Zap,
} from "lucide-react";
import "./carbono-zero-landing.css";
import { resolveAppLoginUrl } from "./landingConfig";

const whatsappBase = "https://wa.me/56966635509";
const email = "cristobal.mundacav@gmail.com";
const logoUrl = "https://mundacasolutions.com/logos/carbono-zero/logo-carbono-zero.png";
const appLoginUrl = resolveAppLoginUrl(import.meta.env.VITE_APP_URL);

const problems = [
  {
    icon: Database,
    title: "Información dispersa",
    text: "Consumos, facturas, planillas y evidencias viven en lugares distintos y nadie ve la operación completa.",
  },
  {
    icon: FileCheck2,
    title: "Reportes que llegan tarde",
    text: "Cuando el impacto aparece al final del periodo, ya se perdió la oportunidad de corregirlo durante la operación.",
  },
  {
    icon: SearchCheck,
    title: "Puntos críticos invisibles",
    text: "Sin una lectura común es difícil saber qué empresa, proyecto, fuente o proceso necesita atención primero.",
  },
  {
    icon: WandSparkles,
    title: "Acciones sin prioridad",
    text: "Reducir emisiones exige contexto: qué cambiar, dónde hacerlo y qué impacto podría generar cada decisión.",
  },
];

const capabilities = [
  {
    icon: CircleGauge,
    title: "Mide con trazabilidad",
    text: "Convierte datos operacionales en CO₂e utilizando factores de emisión, categorías y evidencias asociadas.",
    bullets: ["Registro manual e importación", "Factores de emisión", "Evidencias verificables"],
  },
  {
    icon: BarChart3,
    title: "Monitorea lo que importa",
    text: "Visualiza impacto por empresa, obra, etapa, proceso, fuente y periodo para entender dónde se concentra la huella.",
    bullets: ["KPIs ejecutivos", "Puntos críticos", "Tendencias y comparaciones"],
  },
  {
    icon: WandSparkles,
    title: "Prioriza con inteligencia",
    text: "El copiloto ambiental analiza el contexto de la organización y convierte hallazgos en acciones claras para el equipo.",
    bullets: ["Recomendaciones contextualizadas", "Alertas accionables", "Seguimiento de acciones"],
  },
  {
    icon: FileCheck2,
    title: "Demuestra el avance",
    text: "Ordena evidencias, reportes e indicadores para comunicar resultados con mayor claridad y preparar revisiones internas.",
    bullets: ["Trazabilidad documental", "Reportes regulatorios", "Historial de gestión"],
  },
];

const sectors = [
  {
    icon: Building2,
    name: "Construcción",
    description: "Obras, etapas, materiales, maquinaria, transporte, energía, agua y residuos.",
    items: ["Impacto por obra", "Intensidad por superficie", "Fuentes críticas"],
  },
  {
    icon: Factory,
    name: "Industrial",
    description: "Procesos, consumos energéticos, combustibles, producción y desempeño operacional.",
    items: ["Indicadores por proceso", "Consumo y emisiones", "Alertas operacionales"],
  },
  {
    icon: Truck,
    name: "Transporte",
    description: "Flota, viajes, cargas, combustible, rutas, rendimiento y mantenciones.",
    items: ["Emisiones por viaje", "Rendimiento de flota", "Optimización de rutas"],
  },
  {
    icon: Trees,
    name: "Aserraderos",
    description: "Recepción de trozas, producción, secado, energía, transporte y subproductos.",
    items: ["Trazabilidad de madera", "Consumo energético", "Residuos y valorización"],
  },
];

const steps = [
  {
    number: "01",
    icon: CloudCog,
    title: "Conecta la información",
    text: "Carga datos manualmente, importa planillas o recibe lecturas desde sensores y sistemas externos.",
  },
  {
    number: "02",
    icon: Gauge,
    title: "Calcula y organiza",
    text: "La plataforma transforma la actividad operacional en CO₂e y mantiene la trazabilidad del cálculo.",
  },
  {
    number: "03",
    icon: SearchCheck,
    title: "Detecta dónde actuar",
    text: "Identifica fuentes críticas, variaciones, tendencias y oportunidades concretas de mejora.",
  },
  {
    number: "04",
    icon: Recycle,
    title: "Reduce y demuestra",
    text: "Prioriza acciones, registra avances y comunica resultados con evidencia disponible en un solo lugar.",
  },
];

const sensors = [
  [Zap, "Energía", "Consumo eléctrico y demanda"],
  [Waves, "Agua", "Flujo, consumo y eventos"],
  [RadioTower, "Combustible", "Cargas, uso y rendimiento"],
  [Route, "Movilidad", "GPS, rutas y actividad"],
];

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0 },
};

function Reveal({ children, className = "", delay = 0 }) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      className={className}
      initial={reduceMotion ? false : "hidden"}
      whileInView="visible"
      viewport={{ once: true, amount: 0.16 }}
      variants={fadeUp}
      transition={{ duration: 0.62, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

function Header() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 24);
    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  const close = () => setOpen(false);

  return (
    <header className={`cz-header ${scrolled ? "is-scrolled" : ""}`}>
      <div className="cz-header-shell">
        <a className="cz-brand" href="#inicio" aria-label="Carbono Zero, inicio" onClick={close}>
          <img src={logoUrl} alt="Carbono Zero" />
        </a>

        <nav className={`cz-nav ${open ? "is-open" : ""}`} aria-label="Navegación principal">
          <a href="#plataforma" onClick={close}>Plataforma</a>
          <a href="#sectores" onClick={close}>Sectores</a>
          <a href="#como-funciona" onClick={close}>Cómo funciona</a>
          <a href="#inteligencia" onClick={close}>Inteligencia</a>
          <a href="#contacto" onClick={close}>Contacto</a>
        </nav>

        <div className="cz-header-actions">
          <a className="cz-header-login" href={appLoginUrl}>Ingresar</a>
          <a className="cz-button cz-button-primary cz-header-cta" href="#contacto">
            Solicitar demo <ArrowRight size={16} />
          </a>
          <button
            className="cz-menu-button"
            type="button"
            aria-label={open ? "Cerrar menú" : "Abrir menú"}
            aria-expanded={open}
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <X size={21} /> : <Menu size={21} />}
          </button>
        </div>
      </div>
    </header>
  );
}

function PlatformVisual() {
  return (
    <motion.div
      className="cz-platform-window"
      initial={{ opacity: 0, y: 28, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.85, delay: 0.18, ease: [0.22, 1, 0.36, 1] }}
      aria-label="Vista demostrativa del panel de Carbono Zero"
    >
      <div className="cz-window-top">
        <div className="cz-window-dots"><i /><i /><i /></div>
        <span>Panel ambiental</span>
        <small><i /> Datos actualizados</small>
      </div>
      <div className="cz-window-body">
        <aside>
          <div className="cz-window-mark"><Leaf size={19} /></div>
          <span className="active"><CircleGauge size={15} /> Resumen</span>
          <span><Factory size={15} /> Operación</span>
          <span><BarChart3 size={15} /> Inteligencia</span>
          <span><FileCheck2 size={15} /> Evidencias</span>
        </aside>

        <div className="cz-window-content">
          <div className="cz-window-heading">
            <div><small>VISIÓN EJECUTIVA</small><strong>Gestión ambiental continua</strong></div>
            <span>Multiempresa</span>
          </div>

          <div className="cz-kpi-row">
            <article>
              <span>Impacto total</span>
              <strong>Medición activa</strong>
              <small>Datos consolidados</small>
            </article>
            <article>
              <span>Fuente crítica</span>
              <strong>Combustible</strong>
              <small>Requiere atención</small>
            </article>
            <article>
              <span>Acciones</span>
              <strong>Priorizadas</strong>
              <small>Seguimiento disponible</small>
            </article>
          </div>

          <div className="cz-dashboard-grid">
            <article className="cz-chart-card">
              <div><strong>Emisiones por fuente</strong><small>Vista demostrativa</small></div>
              <div className="cz-bars"><i /><i /><i /><i /><i /></div>
              <div className="cz-chart-labels"><span>Materiales</span><span>Energía</span><span>Transporte</span></div>
            </article>
            <article className="cz-insight-card">
              <div className="cz-insight-icon"><WandSparkles size={18} /></div>
              <small>COPILOTO AMBIENTAL</small>
              <strong>Actúa primero sobre la fuente con mayor impacto.</strong>
              <span>Recomendación basada en el contexto operacional.</span>
            </article>
          </div>
        </div>
      </div>

      <div className="cz-floating-card cz-floating-sensor">
        <RadioTower size={18} />
        <span><strong>Sensores conectados</strong><small>Información en tiempo real</small></span>
        <Check size={15} />
      </div>
      <div className="cz-floating-card cz-floating-alert">
        <Sparkles size={18} />
        <span><strong>Punto crítico detectado</strong><small>Acción sugerida</small></span>
      </div>
    </motion.div>
  );
}

function ContactForm() {
  const [form, setForm] = useState({ name: "", company: "", sector: "Construcción", challenge: "" });

  const message = useMemo(() => {
    const lines = [
      "Hola, quiero solicitar una demostración de Carbono Zero.",
      form.name ? `Nombre: ${form.name}` : "",
      form.company ? `Empresa: ${form.company}` : "",
      form.sector ? `Sector: ${form.sector}` : "",
      form.challenge ? `Desafío: ${form.challenge}` : "",
    ].filter(Boolean);

    return encodeURIComponent(lines.join("\n"));
  }, [form]);

  const handleChange = (field) => (event) => {
    setForm((current) => ({ ...current, [field]: event.target.value }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    window.open(`${whatsappBase}?text=${message}`, "_blank", "noopener,noreferrer");
  };

  return (
    <form className="cz-contact-form" onSubmit={handleSubmit}>
      <div className="cz-form-head">
        <span><b>01</b><strong>Evaluemos tu operación</strong></span>
        <small>Respuesta personal</small>
      </div>
      <div className="cz-form-body">
        <div className="cz-form-grid">
          <label>
            <span>Nombre</span>
            <input value={form.name} onChange={handleChange("name")} placeholder="Tu nombre" required />
          </label>
          <label>
            <span>Empresa</span>
            <input value={form.company} onChange={handleChange("company")} placeholder="Nombre de tu empresa" required />
          </label>
          <label className="full">
            <span>Sector</span>
            <select value={form.sector} onChange={handleChange("sector")}>
              <option>Construcción</option>
              <option>Industrial</option>
              <option>Transporte</option>
              <option>Aserradero / Forestal</option>
              <option>Otro sector productivo</option>
            </select>
          </label>
          <label className="full">
            <span>¿Qué necesitas mejorar?</span>
            <textarea
              value={form.challenge}
              onChange={handleChange("challenge")}
              placeholder="Cuéntanos cómo registran hoy sus datos ambientales y qué les cuesta gestionar."
              rows={5}
              required
            />
          </label>
        </div>
        <div className="cz-form-submit">
          <p>Revisamos cada caso antes de conversar para que la primera reunión sea útil.</p>
          <button className="cz-button cz-button-primary" type="submit">
            Solicitar demostración <ArrowRight size={18} />
          </button>
        </div>
      </div>
    </form>
  );
}

export default function CarbonoZeroLanding() {
  return (
    <div className="cz-landing">
      <a className="cz-skip-link" href="#contenido">Saltar al contenido principal</a>
      <Header />

      <main id="contenido">
        <section className="cz-hero" id="inicio">
          <div className="cz-grid-bg" />
          <div className="cz-hero-glow cz-hero-glow-one" />
          <div className="cz-hero-glow cz-hero-glow-two" />

          <div className="cz-container cz-hero-layout">
            <motion.div
              className="cz-hero-copy"
              initial="hidden"
              animate="visible"
              variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.09 } } }}
            >
              <motion.div className="cz-eyebrow light" variants={fadeUp}>
                <Leaf size={15} /> GESTIÓN AMBIENTAL CONTINUA
              </motion.div>
              <motion.h1 variants={fadeUp}>
                Convierte tus datos operacionales en <span>decisiones que reducen impacto.</span>
              </motion.h1>
              <motion.p variants={fadeUp}>
                Carbono Zero centraliza consumos, materiales, transporte, maquinaria, energía, agua,
                residuos y evidencias para medir CO₂e, detectar puntos críticos y priorizar acciones.
              </motion.p>
              <motion.div className="cz-hero-actions" variants={fadeUp}>
                <a className="cz-button cz-button-primary" href="#contacto">
                  Solicitar demostración <ArrowRight size={19} />
                </a>
                <a className="cz-button cz-button-ghost" href="#plataforma">
                  Ver cómo funciona <ChevronRight size={19} />
                </a>
              </motion.div>
              <motion.div className="cz-trust" variants={fadeUp}>
                <span><Building2 size={16} /> Multiempresa</span>
                <span><Globe2 size={16} /> Multi-rubro</span>
                <span><ShieldCheck size={16} /> Trazabilidad</span>
                <span><RadioTower size={16} /> Datos en tiempo real</span>
              </motion.div>
            </motion.div>

            <PlatformVisual />
          </div>
        </section>

        <section className="cz-proof-strip">
          <div className="cz-container">
            <span><strong>Ganador regional 2026</strong><small>Innovación aplicada a sostenibilidad</small></span>
            <span><strong>Plataforma operativa</strong><small>Disponible en infraestructura cloud</small></span>
            <span><strong>Validación sectorial</strong><small>Construida desde problemas reales</small></span>
          </div>
        </section>

        <section className="cz-section cz-problems">
          <div className="cz-container">
            <Reveal className="cz-heading centered">
              <div className="cz-eyebrow">EL PROBLEMA NO ES MEDIR UNA VEZ</div>
              <h2>Tu huella está ocurriendo todos los días.</h2>
              <p>
                Una planilla puede cerrar un informe. Una plataforma de gestión te permite intervenir
                mientras todavía hay tiempo para mejorar el resultado.
              </p>
            </Reveal>

            <div className="cz-problem-grid">
              {problems.map(({ icon: Icon, title, text }, index) => (
                <Reveal key={title} delay={index * 0.05}>
                  <article className="cz-problem-card">
                    <div><span><Icon size={22} /></span><small>0{index + 1}</small></div>
                    <h3>{title}</h3>
                    <p>{text}</p>
                  </article>
                </Reveal>
              ))}
            </div>

            <Reveal className="cz-inline-cta">
              <div><small>Carbono Zero cambia la lógica</small><strong>De reportar al final a gestionar durante la operación.</strong></div>
              <a href="#contacto">Revisar mi caso <ArrowRight size={18} /></a>
            </Reveal>
          </div>
        </section>

        <section className="cz-section cz-platform" id="plataforma">
          <div className="cz-container">
            <Reveal className="cz-heading split light">
              <div>
                <div className="cz-eyebrow light">UNA PLATAFORMA PARA ACTUAR</div>
                <h2>Información clara para gestionar, decidir y reducir impacto.</h2>
              </div>
              <p>
                Carbono Zero conecta el cálculo ambiental con la operación diaria. Cada módulo existe
                para responder una pregunta que el equipo necesita resolver.
              </p>
            </Reveal>

            <div className="cz-capability-grid">
              {capabilities.map(({ icon: Icon, title, text, bullets }, index) => (
                <Reveal key={title} delay={(index % 2) * 0.06}>
                  <article className="cz-capability-card">
                    <div className="cz-card-head"><span><Icon size={22} /></span><small>0{index + 1}</small></div>
                    <h3>{title}</h3>
                    <p>{text}</p>
                    <ul>{bullets.map((bullet) => <li key={bullet}><Check size={14} /> {bullet}</li>)}</ul>
                  </article>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        <section className="cz-section cz-sectors" id="sectores">
          <div className="cz-container">
            <Reveal className="cz-heading">
              <div className="cz-eyebrow">MULTI-RUBRO DESDE EL DISEÑO</div>
              <h2>Una plataforma, distintas realidades operacionales.</h2>
              <p>
                Cada preset adapta lenguaje, procesos, indicadores y módulos al sector, sin perder una visión
                consolidada para la organización.
              </p>
            </Reveal>

            <div className="cz-sector-grid">
              {sectors.map(({ icon: Icon, name, description, items }, index) => (
                <Reveal key={name} delay={index * 0.05}>
                  <article className="cz-sector-card">
                    <div className="cz-sector-top"><span><Icon size={24} /></span><small>0{index + 1}</small></div>
                    <h3>{name}</h3>
                    <p>{description}</p>
                    <div>{items.map((item) => <span key={item}><Check size={13} /> {item}</span>)}</div>
                  </article>
                </Reveal>
              ))}
            </div>

            <Reveal className="cz-sector-note">
              <Globe2 size={22} />
              <div><strong>Preparado para crecer con tu operación</strong><span>Nuevos sectores, fuentes y procesos pueden incorporarse sin reconstruir la plataforma desde cero.</span></div>
            </Reveal>
          </div>
        </section>

        <section className="cz-section cz-process" id="como-funciona">
          <div className="cz-container cz-process-layout">
            <Reveal className="cz-process-intro">
              <div className="cz-eyebrow">CÓMO FUNCIONA</div>
              <h2>De datos dispersos a una gestión ambiental continua.</h2>
              <p>
                El equipo mantiene el control del proceso completo: desde el origen del dato hasta la acción,
                la evidencia y el reporte.
              </p>
              <div className="cz-process-promise">
                <ShieldCheck size={22} />
                <span><strong>Sin cajas negras</strong><small>Cada resultado conserva contexto, fuente y trazabilidad.</small></span>
              </div>
            </Reveal>

            <div className="cz-step-list">
              {steps.map(({ number, icon: Icon, title, text }, index) => (
                <Reveal key={number} delay={index * 0.05}>
                  <article>
                    <span className="cz-step-number">{number}</span>
                    <div className="cz-step-icon"><Icon size={21} /></div>
                    <div><h3>{title}</h3><p>{text}</p></div>
                  </article>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        <section className="cz-section cz-intelligence" id="inteligencia">
          <div className="cz-container cz-intelligence-layout">
            <Reveal className="cz-intelligence-copy">
              <div className="cz-eyebrow light">COPILOTO AMBIENTAL</div>
              <h2>No necesitas otro dashboard que solo muestre problemas.</h2>
              <p>
                Carbono Zero analiza la información de la empresa, identifica qué está generando impacto
                y orienta al encargado ambiental hacia la siguiente decisión más útil.
              </p>
              <div className="cz-intelligence-points">
                <span><Check size={15} /> Recomendaciones conectadas al contexto real</span>
                <span><Check size={15} /> Priorización según impacto y urgencia</span>
                <span><Check size={15} /> Seguimiento de acciones ambientales</span>
                <span><Check size={15} /> Aprendizaje sobre la operación de cada empresa</span>
              </div>
              <a className="cz-button cz-button-light" href="#contacto">Conocer el copiloto <ArrowRight size={18} /></a>
            </Reveal>

            <Reveal className="cz-ai-panel" delay={0.1}>
              <div className="cz-ai-head">
                <span><WandSparkles size={20} /><b>Asesor ambiental</b></span>
                <small><i /> Analizando operación</small>
              </div>
              <div className="cz-ai-context">
                <small>CONTEXTO ANALIZADO</small>
                <div>
                  <span>Empresa activa</span><span>Fuentes de emisión</span><span>Tendencias</span><span>Evidencias</span>
                </div>
              </div>
              <div className="cz-ai-message">
                <span className="cz-ai-avatar"><Leaf size={19} /></span>
                <div>
                  <small>RECOMENDACIÓN PRIORIZADA</small>
                  <strong>Revisa el consumo de combustible del proceso con mayor variación.</strong>
                  <p>La tendencia reciente concentra el mayor potencial de reducción y requiere validación operacional.</p>
                </div>
              </div>
              <div className="cz-ai-actions"><span>Ver evidencia</span><span>Crear acción</span><span>Asignar responsable</span></div>
            </Reveal>
          </div>
        </section>

        <section className="cz-section cz-iot">
          <div className="cz-container">
            <Reveal className="cz-heading centered">
              <div className="cz-eyebrow">DEL REGISTRO MANUAL AL DATO EN TIEMPO REAL</div>
              <h2>Automatiza la captura sin cambiar de plataforma.</h2>
              <p>
                Comienza con carga manual o importaciones y conecta sensores cuando la operación esté preparada.
                Carbono Zero mantiene una sola fuente de verdad durante toda la evolución.
              </p>
            </Reveal>

            <div className="cz-sensor-grid">
              {sensors.map(([Icon, title, text], index) => (
                <Reveal key={title} delay={index * 0.05}>
                  <article><span><Icon size={22} /></span><div><strong>{title}</strong><small>{text}</small></div><i /></article>
                </Reveal>
              ))}
            </div>

            <Reveal className="cz-iot-flow">
              <span><RadioTower size={21} /> Sensores y sistemas</span>
              <ChevronRight />
              <span><CloudCog size={21} /> Carbono Zero</span>
              <ChevronRight />
              <span><BarChart3 size={21} /> Indicadores</span>
              <ChevronRight />
              <span><WandSparkles size={21} /> Decisiones</span>
            </Reveal>
          </div>
        </section>

        <section className="cz-section cz-contact" id="contacto">
          <div className="cz-container cz-contact-layout">
            <Reveal className="cz-contact-copy">
              <div className="cz-eyebrow light">CONVERSEMOS SOBRE TU OPERACIÓN</div>
              <h2>Descubre dónde Carbono Zero puede generar impacto primero.</h2>
              <p>
                Revisaremos cómo registran hoy la información, qué indicadores necesitan y cuál sería la forma
                más sensata de comenzar. Sin venderte una solución genérica.
              </p>
              <div className="cz-contact-points">
                <span><Check size={16} /> Diagnóstico inicial por sector</span>
                <span><Check size={16} /> Revisión honesta de datos disponibles</span>
                <span><Check size={16} /> Propuesta de implementación por etapas</span>
              </div>
              <a className="cz-direct-link" href={`${whatsappBase}?text=${encodeURIComponent("Hola, quiero conversar sobre Carbono Zero para mi empresa.")}`} target="_blank" rel="noreferrer">
                <MessageCircle size={21} />
                <span><small>¿Prefieres escribir directamente?</small><strong>Estamos a un mensaje de distancia.</strong></span>
                <ArrowRight size={17} />
              </a>
            </Reveal>

            <Reveal delay={0.1}><ContactForm /></Reveal>
          </div>
        </section>
      </main>

      <footer className="cz-footer">
        <div className="cz-container cz-footer-top">
          <div>
            <a className="cz-footer-brand" href="#inicio"><img src={logoUrl} alt="Carbono Zero" /></a>
            <p>Gestión ambiental continua para empresas que necesitan medir, decidir y reducir impacto.</p>
          </div>
          <nav><strong>Plataforma</strong><a href="#plataforma">Capacidades</a><a href="#sectores">Sectores</a><a href="#inteligencia">Copiloto ambiental</a></nav>
          <nav><strong>Contacto</strong><a href="#contacto">Solicitar demo</a><a href={`${whatsappBase}?text=${encodeURIComponent("Hola, quiero conocer Carbono Zero.")}`} target="_blank" rel="noreferrer">WhatsApp</a><a href={`mailto:${email}`}>{email}</a></nav>
          <nav><strong>Acceso</strong><a href={appLoginUrl}>Ingresar a plataforma</a><a href="https://mundacasolutions.com" target="_blank" rel="noreferrer">Mundaca&apos;s Solutions</a></nav>
        </div>
        <div className="cz-container cz-footer-bottom"><span>© {new Date().getFullYear()} Carbono Zero.</span><span>Un producto de Mundaca&apos;s Solutions SpA · Los Ángeles, Chile</span></div>
      </footer>

      <a className="cz-whatsapp" href={`${whatsappBase}?text=${encodeURIComponent("Hola, quiero solicitar una demostración de Carbono Zero.")}`} target="_blank" rel="noreferrer" aria-label="Solicitar demostración por WhatsApp">
        <MessageCircle size={21} /><span>Solicitar demo</span>
      </a>
    </div>
  );
}

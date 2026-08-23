import { useMemo, useState } from "react";
import { Download, ExternalLink, File, FileSpreadsheet, FileWarning, Image as ImageIcon } from "lucide-react";
import { Button } from "@/shared/ui";

const extensionFrom = (...values) => {
  for (const value of values) {
    const clean = String(value || "").split(/[?#]/)[0];
    const match = clean.match(/\.([a-z0-9]+)$/i);
    if (match) return match[1].toLowerCase();
  }
  return "";
};

export function documentPresentation({ url, name, mime }) {
  const extension = extensionFrom(name, url);
  const normalizedMime = String(mime || "").toLowerCase();
  if (normalizedMime.includes("pdf") || extension === "pdf") return { kind: "pdf", extension: "PDF", Icon: File };
  if (normalizedMime.startsWith("image/") || ["png", "jpg", "jpeg", "webp"].includes(extension)) return { kind: "image", extension: extension.toUpperCase() || "Imagen", Icon: ImageIcon };
  if (["csv", "xls", "xlsx"].includes(extension)) return { kind: "file", extension: extension.toUpperCase(), Icon: FileSpreadsheet };
  return { kind: "file", extension: extension.toUpperCase() || "Archivo", Icon: File };
}

export function FileActions({ url, name }) {
  if (!url) return null;
  return <div className="flex flex-wrap gap-2">
    <Button variant="secondary" onClick={() => { const anchor = document.createElement("a"); anchor.href = url; anchor.download = name || ""; anchor.rel = "noreferrer"; anchor.click(); }}><Download aria-hidden="true" size={16} />Descargar</Button>
    <Button onClick={() => window.open(url, "_blank", "noopener,noreferrer")}><ExternalLink aria-hidden="true" size={16} />Abrir original</Button>
  </div>;
}

export default function EvidenceDocumentViewer({ url, name, mime }) {
  const [previewFailed, setPreviewFailed] = useState(false);
  const presentation = useMemo(() => documentPresentation({ url, name, mime }), [mime, name, url]);
  const Icon = previewFailed ? FileWarning : presentation.Icon;

  return <section className="overflow-hidden rounded-[24px] border border-slate-200 bg-slate-100 shadow-[0_16px_40px_rgba(15,23,42,0.08)]">
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3">
      <div className="flex min-w-0 items-center gap-2"><Icon aria-hidden="true" className="shrink-0 text-emerald-700" size={18} /><span className="truncate text-sm font-bold">{name || "Documento original"}</span></div>
      <FileActions url={url} name={name} />
    </div>
    {!url || presentation.kind === "file" || previewFailed ? <div className="flex min-h-[420px] flex-col items-center justify-center p-8 text-center lg:min-h-[680px]">
      <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white text-emerald-700 shadow-sm"><Icon aria-hidden="true" size={30} /></span>
      <h2 className="mt-4 text-xl font-black">{previewFailed ? "No pudimos mostrar una vista previa" : "Vista previa no disponible"}</h2>
      <p className="mt-2 max-w-lg text-sm leading-6 text-[var(--text-muted)]">{previewFailed ? "El archivo sigue disponible y puedes abrirlo directamente." : "Este formato se conserva como evidencia original y puede abrirse con una aplicación compatible."}</p>
      <p className="mt-3 max-w-full truncate font-bold">{name || "Archivo original"} · {presentation.extension}</p>
      <div className="mt-5"><FileActions url={url} name={name} /></div>
    </div> : presentation.kind === "image" ? <div className="flex min-h-[420px] items-center justify-center p-4 lg:min-h-[680px]"><img src={url} alt={`Vista previa de ${name || "la evidencia"}`} className="max-h-[760px] max-w-full object-contain" onError={() => setPreviewFailed(true)} /></div> : <object data={url} type="application/pdf" className="h-[70vh] min-h-[600px] w-full" aria-label={`Vista previa de ${name || "la evidencia"}`}><div className="flex h-full items-center justify-center p-8"><FileActions url={url} name={name} /></div></object>}
  </section>;
}

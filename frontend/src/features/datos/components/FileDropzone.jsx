import { useState } from "react";
import { FileSpreadsheet, Trash2, UploadCloud } from "lucide-react";
import { Button } from "@/shared/ui";

const sizeLabel = (bytes) => bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;

export default function FileDropzone({ file, onChange, disabled = false }) {
  const [dragging, setDragging] = useState(false);
  const acceptFile = (candidate) => {
    if (!candidate || disabled || !/\.(csv|xlsx?)$/i.test(candidate.name)) return;
    onChange(candidate);
  };
  if (file) return <div className="rounded-[18px] border border-emerald-200 bg-emerald-50/60 p-4">
    <div className="flex flex-wrap items-center gap-3">
      <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-emerald-700"><FileSpreadsheet aria-hidden="true" size={19} /></span>
      <div className="min-w-0 flex-1"><p className="truncate font-black">{file.name}</p><p className="text-xs text-[var(--text-muted)]">{sizeLabel(file.size)} · {file.name.split(".").pop()?.toUpperCase()}</p></div>
      <Button size="sm" variant="ghost" leftIcon={Trash2} onClick={() => onChange(null)}>Quitar</Button>
      <label className="inline-flex cursor-pointer items-center justify-center rounded-[var(--radius-md)] border border-[var(--border-default)] bg-white px-3 py-2 text-xs font-bold focus-within:shadow-[var(--focus-ring)]">Reemplazar<input className="sr-only" disabled={disabled} type="file" accept=".csv,.xls,.xlsx" onChange={(event) => acceptFile(event.target.files?.[0])} /></label>
    </div>
  </div>;

  return <label
    onDragEnter={(event) => { event.preventDefault(); if (!disabled) setDragging(true); }}
    onDragOver={(event) => event.preventDefault()}
    onDragLeave={(event) => { event.preventDefault(); setDragging(false); }}
    onDrop={(event) => { event.preventDefault(); setDragging(false); acceptFile(event.dataTransfer.files?.[0]); }}
    className={`flex min-h-40 cursor-pointer flex-col items-center justify-center rounded-[20px] border-2 border-dashed p-6 text-center transition focus-within:shadow-[var(--focus-ring)] ${dragging ? "border-emerald-600 bg-emerald-100/70" : "border-emerald-300 bg-emerald-50/30 hover:bg-emerald-50"}`}
  >
    <UploadCloud aria-hidden="true" className="text-emerald-700" size={28} />
    <span className="mt-3 font-black">Arrastra una planilla o selecciona un archivo</span>
    <span className="mt-1 text-sm text-[var(--text-muted)]">Formatos permitidos: CSV, XLS y XLSX</span>
    <input className="sr-only" disabled={disabled} type="file" accept=".csv,.xls,.xlsx" onChange={(event) => acceptFile(event.target.files?.[0])} />
  </label>;
}

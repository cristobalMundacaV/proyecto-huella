import { useEffect, useMemo, useState } from "react";

import { useConstructoraActiva } from "@/features/constructoras/context/ConstructoraActivaContext";
import { getConstructoraDashboard } from "@/shared/services/api";

function normalizeKpiTitle(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function getKpiOrder(title) {
  const resolvedTitle = normalizeKpiTitle(title);

  if (resolvedTitle.includes("emisiones totales")) return "order-1";
  if (resolvedTitle.includes("evidencia respaldada")) return "order-2";
  if (resolvedTitle.includes("intensidad de carbono")) return "order-3";
  if (resolvedTitle.includes("obra critica")) return "order-4";
  if (resolvedTitle.includes("fuente critica")) return "order-5";
  if (resolvedTitle.includes("categoria critica")) return "order-6";

  return "";
}

function isNumericIdentifier(value) {
  return /^\d+(\.\d+)?$/.test(String(value ?? "").trim());
}

function KpiCard({ detail, icon, title, tone, value }) {
  const { activeConstructoraId } = useConstructoraActiva();
  const [resolvedCriticalWork, setResolvedCriticalWork] = useState("");
  const normalizedTitle = useMemo(() => normalizeKpiTitle(title), [title]);
  const isCriticalWorkCard = normalizedTitle.includes("obra critica");

  useEffect(() => {
    if (!isCriticalWorkCard) {
      setResolvedCriticalWork("");
      return undefined;
    }

    if (!isNumericIdentifier(value)) {
      setResolvedCriticalWork("");
      return undefined;
    }

    if (!activeConstructoraId) {
      setResolvedCriticalWork("");
      return undefined;
    }

    let isCancelled = false;

    getConstructoraDashboard(activeConstructoraId, { light: "1" })
      .then((dashboardData) => {
        if (isCancelled) return;
        setResolvedCriticalWork(dashboardData?.obra_critica || "");
      })
      .catch(() => {
        if (!isCancelled) setResolvedCriticalWork("");
      });

    return () => {
      isCancelled = true;
    };
  }, [activeConstructoraId, isCriticalWorkCard, value]);

  const displayValue = isCriticalWorkCard && resolvedCriticalWork ? resolvedCriticalWork : value;

  const semanticTone = (() => {
    if (typeof tone === "string") {
      return tone;
    }

    if (tone?.background || tone?.border || tone?.color) {
      return tone;
    }

    if (normalizedTitle.includes("emisiones totales") || normalizedTitle.includes("emisiones actuales")) {
      return "danger";
    }

    if (normalizedTitle.includes("evidencia respaldada") || normalizedTitle.includes("maximo potencial") || normalizedTitle.includes("reduccion") || normalizedTitle.includes("viabilidad") || normalizedTitle.includes("potencial")) {
      return "success";
    }

    if (normalizedTitle.includes("intensidad de carbono") || normalizedTitle.includes("escenario recomendado") || normalizedTitle.includes("informacion") || normalizedTitle.includes("operativa") || normalizedTitle.includes("etapa prioritaria")) {
      return "info";
    }

    if (normalizedTitle.includes("obra critica") || normalizedTitle.includes("diesel") || normalizedTitle.includes("concentracion") || normalizedTitle.includes("prioritaria") || normalizedTitle.includes("fuente prioritaria") || normalizedTitle.includes("periodo con mayor emision")) {
      return "warning";
    }

    if (normalizedTitle.includes("riesgo") || normalizedTitle.includes("fuente critica")) {
      return "danger";
    }

    if (normalizedTitle.includes("categoria critica")) {
      return "neutral";
    }

    return "neutral";
  })();

  const toneMap = {
    danger: {
      card: "border-[#FCA5A5] bg-[linear-gradient(180deg,#FEF2F2,#FFF7F7)]",
      icon: "border-[#FCA5A5] bg-white text-[#B42318]",
      title: "text-[#64748B]",
      value: "text-[#B42318]",
      detail: "text-[#B42318]",
    },
    warning: {
      card: "border-[#FED7AA] bg-[linear-gradient(180deg,#FFF7ED,#FFFBF5)]",
      icon: "border-[#FDBA74] bg-white text-[#B45309]",
      title: "text-[#64748B]",
      value: "text-[#B45309]",
      detail: "text-[#B45309]",
    },
    success: {
      card: "border-[#A7F3D0] bg-[linear-gradient(180deg,#ECFDF3,#F7FEFA)]",
      icon: "border-[#A7F3D0] bg-white text-[#047857]",
      title: "text-[#64748B]",
      value: "text-[#047857]",
      detail: "text-[#047857]",
    },
    info: {
      card: "border-[#BFDBFE] bg-[linear-gradient(180deg,#EFF6FF,#F8FBFF)]",
      icon: "border-[#BFDBFE] bg-white text-[#1D4ED8]",
      title: "text-[#64748B]",
      value: "text-[#1D4ED8]",
      detail: "text-[#1D4ED8]",
    },
    neutral: {
      card: "border-[#E2E8F0] bg-[linear-gradient(180deg,#FFFFFF,#F8FAFC)]",
      icon: "border-[#E2E8F0] bg-[#F8FAFC] text-[#334155]",
      title: "text-[#64748B]",
      value: "text-[#334155]",
      detail: "text-[#64748B]",
    },
  }[semanticTone] || {
    card: "border-[#E2E8F0] bg-[linear-gradient(180deg,#FFFFFF,#F8FAFC)]",
    icon: "border-[#E2E8F0] bg-[#F8FAFC] text-[#334155]",
    title: "text-[#64748B]",
    value: "text-[#334155]",
    detail: "text-[#64748B]",
  };

  const toneClasses = toneMap.card;
  const iconClasses = toneMap.icon;
  const titleClasses = toneMap.title;
  const valueClasses = toneMap.value;
  const detailClasses = toneMap.detail;
  const orderClass = getKpiOrder(title);

  return (
    <div className={`rounded-[18px] p-6 shadow-[0_10px_26px_rgba(15,23,42,0.045)] ring-1 ring-white/70 ${toneClasses} ${orderClass}`}>
      <div className="mb-4 flex flex-col items-center text-center">
        <div className={`flex h-11 w-11 items-center justify-center rounded-2xl border shadow-[0_8px_24px_rgba(15,23,42,0.04)] ${iconClasses}`}>
          {icon}
        </div>
        <p className={`mt-3 text-sm font-bold ${titleClasses}`}>{title}</p>
      </div>
      <h3 className={`mt-1 break-words text-center text-2xl font-black tracking-tight ${valueClasses}`}>
        {displayValue}
      </h3>
      {detail && (
        <p className={`mt-2 text-center text-sm font-semibold ${detailClasses}`}>
          {detail}
        </p>
      )}
    </div>
  );
}

export default KpiCard;

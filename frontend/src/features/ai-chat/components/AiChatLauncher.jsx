import { useState } from "react";
import { Sparkles } from "lucide-react";

import { usePermissions } from "@/features/auth/hooks/usePermissions";
import { useOrganizacionActiva } from "@/features/organizaciones/context/OrganizacionActivaContext";
import AiChatPanel from "./AiChatPanel";

export default function AiChatLauncher() {
  const [open, setOpen] = useState(false);
  const { can } = usePermissions();
  const { activeOrganizacionId } = useOrganizacionActiva();

  if (!activeOrganizacionId || !can("intelligence_chat.view")) return null;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Abrir Carbono Zero Intelligence"
        className="fixed bottom-5 right-5 z-40 flex h-13 w-13 items-center justify-center rounded-full bg-[var(--brand-primary)] text-white shadow-[0_10px_30px_rgba(16,185,129,0.35)] transition hover:bg-[var(--brand-hover)] focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]"
        style={{ height: 52, width: 52 }}
      >
        <Sparkles size={22} />
      </button>
      {open && <AiChatPanel onClose={() => setOpen(false)} />}
    </>
  );
}

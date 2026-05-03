import { EmpresaActivaProvider } from "@/features/empresas/context/EmpresaActivaContext";

function Providers({ children }) {
  return <EmpresaActivaProvider>{children}</EmpresaActivaProvider>;
}

export default Providers;

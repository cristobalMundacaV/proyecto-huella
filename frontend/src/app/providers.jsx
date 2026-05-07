import { EmpresaActivaProvider } from "@/features/empresas/context/EmpresaActivaContext";
import { FactoresProvider } from "@/features/factores/context/FactoresContext";

function Providers({ children }) {
  return (
    <EmpresaActivaProvider>
      <FactoresProvider>{children}</FactoresProvider>
    </EmpresaActivaProvider>
  );
}

export default Providers;

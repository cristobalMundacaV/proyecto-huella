import { AuthProvider } from "@/features/auth/context/AuthContext";
import { EmpresaActivaProvider } from "@/features/empresas/context/EmpresaActivaContext";
import { FactoresProvider } from "@/features/factores/context/FactoresContext";

function Providers({ children }) {
  return (
    <AuthProvider>
      <EmpresaActivaProvider>
        <FactoresProvider>{children}</FactoresProvider>
      </EmpresaActivaProvider>
    </AuthProvider>
  );
}

export default Providers;

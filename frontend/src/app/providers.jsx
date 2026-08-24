import { AuthProvider } from "@/features/auth/context/AuthContext";
import { OrganizacionActivaProvider } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { FactoresProvider } from "@/features/factores/context/FactoresContext";
import { OperationalWorkspaceProvider } from "@/features/workspace/context/OperationalWorkspaceContext";

function Providers({ children }) {
  return (
    <AuthProvider>
      <OrganizacionActivaProvider>
        <OperationalWorkspaceProvider><FactoresProvider>{children}</FactoresProvider></OperationalWorkspaceProvider>
      </OrganizacionActivaProvider>
    </AuthProvider>
  );
}

export default Providers;

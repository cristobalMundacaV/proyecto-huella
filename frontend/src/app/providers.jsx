import { AuthProvider } from "@/features/auth/context/AuthContext";
import { OrganizacionActivaProvider } from "@/features/organizaciones/context/OrganizacionActivaContext";
import { FactoresProvider } from "@/features/factores/context/FactoresContext";

function Providers({ children }) {
  return (
    <AuthProvider>
      <OrganizacionActivaProvider>
        <FactoresProvider>{children}</FactoresProvider>
      </OrganizacionActivaProvider>
    </AuthProvider>
  );
}

export default Providers;

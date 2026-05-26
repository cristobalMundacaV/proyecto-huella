import { AuthProvider } from "@/features/auth/context/AuthContext";
import { ConstructoraActivaProvider } from "@/features/constructoras/context/ConstructoraActivaContext";
import { FactoresProvider } from "@/features/factores/context/FactoresContext";

function Providers({ children }) {
  return (
    <AuthProvider>
      <ConstructoraActivaProvider>
        <FactoresProvider>{children}</FactoresProvider>
      </ConstructoraActivaProvider>
    </AuthProvider>
  );
}

export default Providers;

import App from "./App.jsx";
import Providers from "./providers.jsx";
import VerificarLote from "@/features/lotes/pages/VerificarLote.jsx";

function Root() {
  if (window.location.pathname.startsWith("/verificar/")) {
    return (
      <Providers>
        <VerificarLote />
      </Providers>
    );
  }

  return (
    <Providers>
      <App />
    </Providers>
  );
}

export default Root;

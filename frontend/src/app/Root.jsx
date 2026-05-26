import App from "./App.jsx";
import Providers from "./providers.jsx";
import VerificarObra from "@/features/obras/pages/VerificarObra.jsx";

function Root() {
  if (window.location.pathname.startsWith("/verificar/")) {
    return (
      <Providers>
        <VerificarObra />
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

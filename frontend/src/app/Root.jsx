import App from "./App.jsx";
import Providers from "./providers.jsx";
import VerificarObra from "@/features/obras/pages/VerificarObra.jsx";
import CarbonoZeroLanding from "@/landing/CarbonoZeroLanding.jsx";

function Root() {
  const pathname = window.location.pathname;

  if (pathname.startsWith("/verificar/")) {
    return (
      <Providers>
        <VerificarObra />
      </Providers>
    );
  }

  if (pathname === "/" || pathname === "") {
    return <CarbonoZeroLanding />;
  }

  return (
    <Providers>
      <App />
    </Providers>
  );
}

export default Root;

import { BrowserRouter } from "react-router-dom";
import AppRouter from "./router/router";

export default function Root() {
  return <BrowserRouter><AppRouter /></BrowserRouter>;
}

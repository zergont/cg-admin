import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { OverviewPage } from "./pages/OverviewPage";
import { ServicePage } from "./pages/ServicePage";
import { UpdatesPage } from "./pages/UpdatesPage";
import { AuditPage } from "./pages/AuditPage";
import { DiagnosticsPage } from "./pages/DiagnosticsPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<OverviewPage />} />
        <Route path="service/:unit" element={<ServicePage />} />
        <Route path="updates" element={<UpdatesPage />} />
        <Route path="audit" element={<AuditPage />} />
        <Route path="diagnostics" element={<DiagnosticsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

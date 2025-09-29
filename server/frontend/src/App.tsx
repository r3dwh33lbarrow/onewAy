import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";

import LoginPanel from "./components/LoginPanel";
import ProtectedRoute from "./components/ProtectedRoute";
import RegisterPanel from "./components/RegisterPanel";
import NotFound from "./pages/404";
import ClientPageWrapper from "./pages/ClientPageWrapper";
import ConsolePageWrapper from "./pages/ConsolePageWrapper";
import Dashboard from "./pages/Dashboard";
import ModulePageWrapper from "./pages/ModulePageWrapper";
import ModulesPage from "./pages/ModulesPage";
import SettingsPage from "./pages/SettingsPage";
import { Login, Register } from "./services/authentication";
import { useAuthStore } from "./stores/authStore";

export default function App() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={
            <Navigate to={isAuthenticated ? "/dashboard" : "/login"} replace />
          }
        />
        <Route path="/login" element={<LoginPanel onSubmit={Login} />} />
        <Route
          path="/register"
          element={<RegisterPanel onSubmit={Register} />}
        />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/client/:username"
          element={
            <ProtectedRoute>
              <ClientPageWrapper />
            </ProtectedRoute>
          }
        />
        <Route
          path="/modules/:name"
          element={
            <ProtectedRoute>
              <ModulePageWrapper />
            </ProtectedRoute>
          }
        />
        <Route
          path="/modules"
          element={
            <ProtectedRoute>
              <ModulesPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <SettingsPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/console/:username"
          element={
            <ProtectedRoute>
              <ConsolePageWrapper />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}

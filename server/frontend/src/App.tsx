import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";

import { apiClient, type ApiError } from "./apiClient";
import LoginPanel from "./components/LoginPanel";
import ProtectedRoute from "./components/ProtectedRoute";
import RegisterPanel from "./components/RegisterPanel";
import NotFound from "./pages/404";
import ClientPage from "./pages/ClientPage";
import ConsolePage from "./pages/ConsolePage";
import Dashboard from "./pages/Dashboard";
import ModulePage from "./pages/ModulePage";
import ModulesPage from "./pages/ModulesPage";
import SettingsPage from "./pages/SettingsPage";
import type { AuthRequest } from "./schemas/authentication";
import type { BasicTaskResponse } from "./schemas/general";
import { useAuthStore } from "./stores/authStore";

export default function App() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  const Login = (data: AuthRequest): Promise<BasicTaskResponse | ApiError> =>
    apiClient.post<AuthRequest, BasicTaskResponse>("/user/auth/login", data);

  const Register = (data: AuthRequest): Promise<BasicTaskResponse | ApiError> =>
    apiClient.post<AuthRequest, BasicTaskResponse>("/user/auth/register", data);

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
              <ClientPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/modules/:name"
          element={
            <ProtectedRoute>
              <ModulePage />
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
              <ConsolePage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}

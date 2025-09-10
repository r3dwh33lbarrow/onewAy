import LoginPanel from "./components/LoginPanel.tsx";
import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
import { Login, Register } from "./services/authentication.ts";
import RegisterPanel from "./components/RegisterPanel.tsx";
import Dashboard from "./pages/Dashboard.tsx";
import ProtectedRoute from "./components/ProtectedRoute.tsx";
import {useAuthStore} from "./stores/authStore.ts";
import ClientPageWrapper from "./pages/ClientPageWrapper.tsx";
import NotFound from "./pages/404.tsx";
import ModulesPage from "./pages/ModulesPage.tsx";
import ModulePageWrapper from "./pages/ModulePageWrapper.tsx";

export default function App() {
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);

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
        <Route path="/register" element={<RegisterPanel onSubmit={Register} />} />
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
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}
import LoginPanel from "./componets/LoginPanel.tsx";
  import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
  import { Login, Register } from "./services/authentication.ts";
  import RegisterPanel from "./componets/RegisterPanel.tsx";
  import Dashboard from "./componets/Dashboard.tsx";
  import ProtectedRoute from "./componets/ProtectedRoute.tsx";
  import {useAuthStore} from "./stores/authStore.ts";

  function App() {
    const isAuthenticated = useAuthStore(state => state.isAuthenticated);

    return (
      <BrowserRouter>
        <Routes>
          <Route path="/" element={
            <Navigate to={isAuthenticated ? "/dashboard" : "/login"} replace />
          } />
          <Route path="/login" element={<LoginPanel onSubmit={Login} />} />
          <Route path="/register" element={<RegisterPanel onSubmit={Register} />} />
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } />
        </Routes>
      </BrowserRouter>
    );
  }

  export default App;
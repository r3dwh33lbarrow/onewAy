import LoginPanel from "./componets/LoginPanel.tsx";
import {BrowserRouter, Route, Routes} from "react-router-dom";
import {Login, Register} from "./services/authentication.ts";
import RegisterPanel from "./componets/RegisterPanel.tsx";
import Dashboard from "./componets/Dashboard.tsx";
import ProtectedRoute from "./componets/ProtectedRoute.tsx";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path='/login' element={<LoginPanel onSubmit={Login}/>}/>
        <Route path='/register' element={<RegisterPanel onSubmit={Register}/>}/>
        <Route path='/dashboard' element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }/>
      </Routes>
    </BrowserRouter>
  )
}

export default App;

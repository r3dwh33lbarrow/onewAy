import LoginPanel from "./componets/LoginPanel.tsx";
import {BrowserRouter, Route, Routes} from "react-router-dom";
import {Login, Register} from "./services/authentication.ts";
import RegisterPanel from "./componets/RegisterPanel.tsx";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path='/login' element={<LoginPanel onSubmit={Login} />}/>
        <Route path='/register' element={<RegisterPanel onSubmit={Register} />}/>
      </Routes>
    </BrowserRouter>
  )
}

export default App;

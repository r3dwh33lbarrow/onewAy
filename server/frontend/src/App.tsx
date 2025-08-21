import LoginPanel from "./componets/LoginPanel.tsx";
import {BrowserRouter, Route, Routes} from "react-router-dom";
import {Login} from "./services/authentication.ts";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path='/login' element={<LoginPanel onSubmit={Login} />}/>
      </Routes>
    </BrowserRouter>
  )
}

export default App;

import {BrowserRouter, Routes, Route} from "react-router-dom"
import ProtectedRoute from "./components/ProtectedRoute"

import Login from "./pages/Login"
import Register from "./pages/Register"
import Dashboard from "./pages/Dashboard"
import Projects from "./pages/Project"
import ProjectDetails from "./pages/ProjectDetails"



function App(){
  return(
    <BrowserRouter>
    <Routes>
      <Route path='/register' element={<Register/>}/>
      <Route path='/login' element={<Login/>}/>
      <Route 
          path="/dashboard" 
          element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
          } />
    <Route 
          path="/projects" 
          element={
          <ProtectedRoute>
            <Projects />
          </ProtectedRoute>
          } 
          />
      <Route 
          path="/projects/:project_id" 
          element={
          <ProtectedRoute>
            <ProjectDetails/>
          </ProtectedRoute>
          } 
          />
    </Routes>
    </BrowserRouter>
  )
}

export default App
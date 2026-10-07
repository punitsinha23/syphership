import {BrowserRouter, Routes, Route} from "react-router-dom"
import ProtectedRoute from "./components/ProtectedRoute/ProtectedRoute"
import { SpaceBackground } from "./components/SpaceBackground/SpaceBackground"
import { RocketCursor } from "./components/RocketCursor/RocketCursor"

import Login from "./pages/Login/Login"
import Register from "./pages/Register/Register"
import Dashboard from "./pages/Dashboard/Dashboard"
import Projects from "./pages/Project/Project"
import ProjectDetails from "./pages/ProjectDetails/ProjectDetails"
import DeploymentDetails from "./pages/DeploymentDetails/DeploymentDetails"



function App(){
  return(
    <BrowserRouter>
    <SpaceBackground />
    <RocketCursor />
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
      <Route
          path="/deployments/:deployment_id"
          element={
            <ProtectedRoute>
              <DeploymentDetails/>
            </ProtectedRoute>
          }
          />
    </Routes>
    </BrowserRouter>
  )
}

export default App
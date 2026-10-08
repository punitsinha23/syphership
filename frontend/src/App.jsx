import {BrowserRouter, Routes, Route, Navigate} from "react-router-dom"
import ProtectedRoute from "./components/ProtectedRoute/ProtectedRoute"
import { SpaceBackground } from "./components/SpaceBackground/SpaceBackground"
import { EngineTrail } from "./components/EngineTrail/EngineTrail"

import Landing from "./pages/Landing/Landing"
import Login from "./pages/Login/Login"
import Dashboard from "./pages/Dashboard/Dashboard"
import Projects from "./pages/Project/Project"
import ProjectDetails from "./pages/ProjectDetails/ProjectDetails"
import DeploymentDetails from "./pages/DeploymentDetails/DeploymentDetails"
import AuthCallback from "./pages/AuthCallback/AuthCallback"



function App(){
  return(
    <BrowserRouter>
    <SpaceBackground />
    <EngineTrail />
    <Routes>
      <Route path='/' element={<Landing/>}/>
      <Route path='/login' element={<Login/>}/>
      {/* Sign-up and sign-in are the same OAuth flow */}
      <Route path='/register' element={<Navigate to="/login" replace/>}/>
      <Route path='/auth/callback' element={<AuthCallback/>}/>
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
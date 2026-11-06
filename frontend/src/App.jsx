import {BrowserRouter, Routes, Route, Navigate} from "react-router-dom"
import ProtectedRoute from "./components/ProtectedRoute/ProtectedRoute"
import { SpaceBackground } from "./components/SpaceBackground/SpaceBackground"
import { EngineTrail } from "./components/EngineTrail/EngineTrail"
import { ScrollToTop } from "./components/ScrollToTop/ScrollToTop"

import Landing from "./pages/Landing/Landing"
import About from "./pages/About/About"
import HowItWorks from "./pages/HowItWorks/HowItWorks"
import Docs from "./pages/Docs/Docs"
import Privacy from "./pages/Legal/Privacy"
import Terms from "./pages/Legal/Terms"
import Settings from "./pages/Settings/Settings"
import Login from "./pages/Login/Login"
import Dashboard from "./pages/Dashboard/Dashboard"
import Projects from "./pages/Project/Project"
import ProjectDetails from "./pages/ProjectDetails/ProjectDetails"
import DeploymentDetails from "./pages/DeploymentDetails/DeploymentDetails"
import AuthCallback from "./pages/AuthCallback/AuthCallback"
import NotFound from "./pages/NotFound/NotFound"



function App(){
  return(
    <BrowserRouter>
    <ScrollToTop />
    <SpaceBackground />
    <EngineTrail />
    <Routes>
      <Route path='/' element={<Landing/>}/>
      <Route path='/about' element={<About/>}/>
      <Route path='/how-it-works' element={<HowItWorks/>}/>
      <Route path='/docs' element={<Docs/>}/>
      <Route path='/privacy' element={<Privacy/>}/>
      <Route path='/terms' element={<Terms/>}/>
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
      <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <Settings/>
            </ProtectedRoute>
          }
          />
      <Route path="*" element={<NotFound/>}/>
    </Routes>
    </BrowserRouter>
  )
}

export default App
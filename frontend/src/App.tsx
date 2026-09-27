import { Navigate, Route, Routes } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Assistant from "./pages/Assistant";
import BudgetSimulator from "./pages/BudgetSimulator";
import Dashboard from "./pages/Dashboard";
import DataUpload from "./pages/DataUpload";
import Landing from "./pages/Landing";
import LocalityAnalysis from "./pages/LocalityAnalysis";
import Reports from "./pages/Reports";
import Rooftops from "./pages/Rooftops";
import Scenarios from "./pages/Scenarios";
import SolarMap from "./pages/SolarMap";

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="layout">
      <Sidebar />
      <div className="main">{children}</div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/dashboard" element={<Shell><Dashboard /></Shell>} />
      <Route path="/map" element={<Shell><SolarMap /></Shell>} />
      <Route path="/localities" element={<Shell><LocalityAnalysis /></Shell>} />
      <Route path="/rooftops" element={<Shell><Rooftops /></Shell>} />
      <Route path="/budget" element={<Shell><BudgetSimulator /></Shell>} />
      <Route path="/scenarios" element={<Shell><Scenarios /></Shell>} />
      <Route path="/assistant" element={<Shell><Assistant /></Shell>} />
      <Route path="/reports" element={<Shell><Reports /></Shell>} />
      <Route path="/data" element={<Shell><DataUpload /></Shell>} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

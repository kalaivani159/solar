import { NavLink } from "react-router-dom";

const PRIMARY = [
  { to: "/dashboard", label: "Dashboard", ico: "▦" },
  { to: "/map", label: "Solar Map", ico: "◈" },
  { to: "/localities", label: "Locality Analysis", ico: "◍" },
  { to: "/rooftops", label: "Rooftops", ico: "▤" },
];

const PLANNING = [
  { to: "/budget", label: "Budget Simulator", ico: "₹" },
  { to: "/scenarios", label: "Scenarios", ico: "⇄" },
  { to: "/assistant", label: "AI Assistant", ico: "✦" },
  { to: "/reports", label: "Reports", ico: "▣" },
];

const DATA = [{ to: "/data", label: "Data Management", ico: "⬒" }];

function Group({ title, items }: { title: string; items: typeof PRIMARY }) {
  return (
    <>
      <div className="nav-section">{title}</div>
      {items.map((item) => (
        <NavLink key={item.to} to={item.to}>
          <span className="nav-ico">{item.ico}</span>
          {item.label}
        </NavLink>
      ))}
    </>
  );
}

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <h1>SolarSphere AI</h1>
        <div className="brand-sub">Government Solar Planning</div>
        <span className="brand-tag">Feature 3</span>
      </div>
      <nav className="nav">
        <Group title="Planning" items={PRIMARY} />
        <Group title="Decision support" items={PLANNING} />
        <Group title="Data" items={DATA} />
      </nav>
      <div className="sidebar-foot">
        Solar Potential Index is a project decision-support score (0–100), not an official
        government rating.
      </div>
    </aside>
  );
}

export default function PageHeader({
  title,
  subtitle,
  right,
}: {
  title: string;
  subtitle: string;
  right?: React.ReactNode;
}) {
  return (
    <header className="topbar">
      <div>
        <h2>{title}</h2>
        <div className="sub">{subtitle}</div>
      </div>
      <div className="topbar-right">{right}</div>
    </header>
  );
}

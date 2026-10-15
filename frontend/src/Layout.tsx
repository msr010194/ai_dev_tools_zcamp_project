import { NavLink, Outlet } from "react-router-dom";

const links = [
  { to: "/", label: "Home", end: true },
  { to: "/timeline", label: "Timeline" },
  { to: "/tags", label: "Tags" },
  { to: "/collections", label: "Collections" },
];

export default function Layout() {
  return (
    <>
      <nav aria-label="Main">
        {links.map((l) => (
          <NavLink key={l.to} to={l.to} end={l.end} style={{ marginRight: 12 }}>
            {l.label}
          </NavLink>
        ))}
      </nav>
      <main>
        <Outlet />
      </main>
    </>
  );
}

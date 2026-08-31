import { Link, NavLink } from "react-router-dom";

const PANEL_URL = import.meta.env.VITE_PANEL_URL ?? "http://localhost:5174";

export function SiteHeader() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4">
        <Link to="/" className="text-lg font-semibold tracking-tight text-slate-900">
          Teamos
        </Link>
        <nav className="hidden items-center gap-6 text-sm text-slate-600 sm:flex">
          <NavLink to="/features" className="hover:text-slate-900">
            Features
          </NavLink>
          <NavLink to="/pricing" className="hover:text-slate-900">
            Pricing
          </NavLink>
          <NavLink to="/about" className="hover:text-slate-900">
            About
          </NavLink>
        </nav>
        <div className="flex items-center gap-3 text-sm">
          <Link to="/login" className="font-medium text-slate-700 hover:text-slate-900">
            Sign in
          </Link>
          <Link
            to="/register"
            className="rounded-md bg-teal-700 px-3 py-2 font-medium text-white hover:bg-teal-800"
          >
            Get started
          </Link>
        </div>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="border-t border-slate-200 bg-slate-50">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-8 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between">
        <p>Teamos — lightweight team management for engineering managers.</p>
        <div className="flex gap-4">
          <Link to="/features" className="hover:text-slate-900">
            Features
          </Link>
          <Link to="/pricing" className="hover:text-slate-900">
            Pricing
          </Link>
          <Link to="/about" className="hover:text-slate-900">
            About
          </Link>
          <a href={`${PANEL_URL}/login`} className="hover:text-slate-900">
            Panel
          </a>
        </div>
      </div>
    </footer>
  );
}

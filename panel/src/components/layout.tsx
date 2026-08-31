import { NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/hooks/useAuth";
import { displayName } from "@/lib/format";
import { getCurrentOrganization } from "@/services/organizations";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/teams", label: "Teams" },
  { to: "/projects", label: "Projects" },
  { to: "/tasks", label: "Tasks" },
  { to: "/goals", label: "Goals" },
  { to: "/checkins", label: "Check-ins" },
  { to: "/organization", label: "Organization" },
  { to: "/organization/members", label: "Members" },
  { to: "/settings", label: "Settings" },
];

export function AppLayout() {
  const { user, logout } = useAuth();
  const orgQuery = useQuery({
    queryKey: ["organizations", "current"],
    queryFn: getCurrentOrganization,
  });

  return (
    <div className="min-h-screen lg:flex">
      <aside className="flex w-full flex-col border-b border-slate-800 bg-slate-900 text-slate-100 lg:min-h-screen lg:w-60 lg:border-b-0 lg:border-r">
        <div className="border-b border-slate-800 px-4 py-4">
          <p className="text-sm font-semibold tracking-wide text-white">Teamos</p>
          <p className="mt-1 truncate text-xs text-slate-400">
            {orgQuery.data?.name ?? "Workspace"}
          </p>
        </div>
        <nav className="flex gap-1 overflow-x-auto p-2 lg:flex-1 lg:flex-col">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm whitespace-nowrap ${
                  isActive ? "bg-teal-700 text-white" : "text-slate-300 hover:bg-slate-800"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="flex items-center justify-between gap-2 border-t border-slate-800 px-4 py-3">
          <div className="min-w-0">
            <p className="truncate text-sm text-white">
              {user ? displayName(user.first_name, user.last_name) : ""}
            </p>
            <p className="truncate text-xs text-slate-400">{user?.email}</p>
          </div>
          <button
            type="button"
            onClick={logout}
            className="text-xs font-medium text-slate-300 hover:text-white"
          >
            Log out
          </button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 p-4 sm:p-6 lg:p-8">
        <Outlet />
      </main>
    </div>
  );
}

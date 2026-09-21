import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "@/components/layout";
import { AuthCallbackPage } from "@/features/auth/AuthCallbackPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { FeedbackPage } from "@/features/feedback/FeedbackPage";
import { GoalsPage } from "@/features/goals/GoalsPage";
import { MeetingsPage } from "@/features/meetings/MeetingsPage";
import { OrganizationMembersPage, OrganizationPage } from "@/features/organization/OrganizationPage";
import { ProjectCreatePage } from "@/features/projects/ProjectCreatePage";
import { ProjectDetailPage } from "@/features/projects/ProjectDetailPage";
import { ProjectsPage } from "@/features/projects/ProjectsPage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { TasksPage } from "@/features/tasks/TasksPage";
import { TeamDetailPage } from "@/features/teams/TeamDetailPage";
import { TeamsPage } from "@/features/teams/TeamsPage";
import { GuestRoute, ProtectedRoute } from "@/routes/guards";

export function App() {
  return (
    <Routes>
      <Route path="/auth/callback" element={<AuthCallbackPage />} />
      <Route element={<GuestRoute />}>
        <Route path="/login" element={<LoginPage />} />
      </Route>
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/teams" element={<TeamsPage />} />
          <Route path="/teams/:id" element={<TeamDetailPage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/new" element={<ProjectCreatePage />} />
          <Route path="/projects/:id" element={<ProjectDetailPage />} />
          <Route path="/tasks" element={<TasksPage />} />
          <Route path="/goals" element={<GoalsPage />} />
          <Route path="/meetings" element={<MeetingsPage />} />
          <Route path="/feedback" element={<FeedbackPage />} />
          <Route path="/organization" element={<OrganizationPage />} />
          <Route path="/organization/members" element={<OrganizationMembersPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Route>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

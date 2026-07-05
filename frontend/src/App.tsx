import { Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import ErrorBoundary from "./components/ErrorBoundary";
import Gate from "./components/Gate";
import Header from "./components/Header";
import MatchesList from "./pages/MatchesList";
import ProfileForm from "./pages/ProfileForm";
import Register from "./pages/Register";
import SchedulesPage from "./pages/SchedulesPage";
import SearchPage from "./pages/SearchPage";
import { useTheme } from "./hooks/useTheme";
import { useProfile } from "./lib/profile-context";

export default function App() {
  const { theme, toggle } = useTheme();
  const { profileId } = useProfile();

  return (
    <div className="min-h-screen bg-app text-fg">
      {profileId === null ? (
        <Routes>
          <Route path="/register" element={<Register />} />
          <Route path="*" element={<Gate theme={theme} onToggleTheme={toggle} />} />
        </Routes>
      ) : (
        <ErrorBoundary>
          <Header theme={theme} onToggleTheme={toggle} />
          <Routes>
            <Route path="/" element={<MatchesList />} />
            <Route path="/matches/:jobId" element={<MatchesList />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/programaciones" element={<SchedulesPage />} />
            <Route path="/profile" element={<ProfileForm />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ErrorBoundary>
      )}
      <Toaster theme={theme} position="bottom-right" />
    </div>
  );
}

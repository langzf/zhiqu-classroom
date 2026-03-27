import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthGuard } from './authGuard';
import AppLayout from '@/components/layout/AppLayout';
import LoginPage from '@/pages/login/LoginPage';
import DashboardPage from '@/pages/dashboard/DashboardPage';
import TextbookList from '@/pages/textbooks/TextbookList';
import TextbookDetail from '@/pages/textbooks/TextbookDetail';

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/"
        element={
          <AuthGuard>
            <AppLayout />
          </AuthGuard>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="textbooks" element={<TextbookList />} />
        <Route path="textbooks/:id" element={<TextbookDetail />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

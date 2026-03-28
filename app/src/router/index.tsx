import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom';
import { MainLayout } from '@/layouts/MainLayout';
import { AuthGuard } from '@/components/AuthGuard';

export const router = createBrowserRouter([
  {
    path: '/login',
    lazy: () => import('@/pages/LoginPage'),
  },
  {
    path: '/',
    element: (
      <AuthGuard>
        <MainLayout />
      </AuthGuard>
    ),
    children: [
      { index: true, lazy: () => import('@/pages/HomePage') },
      { path: 'study', lazy: () => import('@/pages/StudyPage') },
      { path: 'chat', lazy: () => import('@/pages/ChatPage') },
      { path: 'profile', lazy: () => import('@/pages/ProfilePage') },
    ],
  },
  // Detail pages — full screen (no tab bar), auth required
  {
    element: (
      <AuthGuard>
        <Outlet />
      </AuthGuard>
    ),
    children: [
      { path: '/textbook/:id', lazy: () => import('@/pages/TextbookDetailPage') },
      { path: '/chapter/:id', lazy: () => import('@/pages/ChapterDetailPage') },
      { path: '/conversation/:id', lazy: () => import('@/pages/ConversationPage') },
      { path: '/task/:id', lazy: () => import('@/pages/TaskDetailPage') },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
]);

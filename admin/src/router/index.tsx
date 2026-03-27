import { createBrowserRouter, Navigate } from 'react-router-dom';
import { lazy } from 'react';
import AppLayout from '@/components/layout/AppLayout';
import AuthGuard from '@/router/authGuard';

const LoginPage = lazy(() => import('@/pages/login/LoginPage'));
const DashboardPage = lazy(() => import('@/pages/dashboard/DashboardPage'));
const TextbookList = lazy(() => import('@/pages/textbooks/TextbookList'));
const TextbookDetail = lazy(() => import('@/pages/textbooks/TextbookDetail'));
const ExerciseList = lazy(() => import('@/pages/exercises/ExerciseList'));
const ConversationList = lazy(() => import('@/pages/tutor/ConversationList'));
const ChatPage = lazy(() => import('@/pages/tutor/ChatPage'));
const UserList = lazy(() => import('@/pages/users/UserList'));
const TaskList = lazy(() => import('@/pages/learning/TaskList'));

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: (
      <AuthGuard>
        <AppLayout />
      </AuthGuard>
    ),
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'textbooks', element: <TextbookList /> },
      { path: 'textbooks/:id', element: <TextbookDetail /> },
      { path: 'exercises', element: <ExerciseList /> },
      { path: 'tutor', element: <ConversationList /> },
      { path: 'tutor/:id', element: <ChatPage /> },
      { path: 'users', element: <UserList /> },
      { path: 'tasks', element: <TaskList /> },
    ],
  },
]);

export default router;

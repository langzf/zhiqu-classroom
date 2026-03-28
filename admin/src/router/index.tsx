import React, { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom';
import { Spin } from 'antd';
import AppLayout from '@/components/layout/AppLayout';
import AuthGuard from './authGuard';

// Lazy-loaded pages
const LoginPage = lazy(() => import('@/pages/login/LoginPage'));
const DashboardPage = lazy(() => import('@/pages/dashboard/DashboardPage'));
const TextbookList = lazy(() => import('@/pages/textbooks/TextbookList'));
const TextbookDetail = lazy(() => import('@/pages/textbooks/TextbookDetail'));
const ExerciseList = lazy(() => import('@/pages/exercises/ExerciseList'));
const ConversationList = lazy(() => import('@/pages/tutor/ConversationList'));
const ChatPage = lazy(() => import('@/pages/tutor/ChatPage'));
const UserList = lazy(() => import('@/pages/users/UserList'));
const TaskList = lazy(() => import('@/pages/learning/TaskList'));

const LazyWrapper: React.FC = () => (
  <Suspense
    fallback={
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" tip="加载中..." />
      </div>
    }
  >
    <Outlet />
  </Suspense>
);

export const router = createBrowserRouter([
  {
    path: '/login',
    element: (
      <Suspense fallback={<Spin size="large" />}>
        <LoginPage />
      </Suspense>
    ),
  },
  {
    element: <AuthGuard />,
    children: [
      {
        element: <AppLayout />,
        children: [
          {
            element: <LazyWrapper />,
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
        ],
      },
    ],
  },
  { path: '*', element: <Navigate to="/dashboard" replace /> },
]);

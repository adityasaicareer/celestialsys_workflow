import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../lib/auth';
import Loading from './Loading';

interface ProtectedRouteProps {
  children: React.ReactNode;
  roles?: string[];
}

export default function ProtectedRoute({ children, roles }: ProtectedRouteProps) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace('/login');
    if (!loading && user && roles && !roles.includes(user.role)) router.replace('/dashboard');
  }, [loading, user, roles, router]);

  if (loading || !user || (roles && !roles.includes(user.role))) return <Loading label="Checking access" />;
  return <>{children}</>;
}

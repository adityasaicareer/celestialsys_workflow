import { useEffect } from 'react';
import { useRouter } from 'next/router';
import Loading from '../components/Loading';

export default function Home() {
  const router = useRouter();
  useEffect(() => { router.replace('/dashboard'); }, [router]);
  return <Loading label="Loading Gatekeeper" />;
}

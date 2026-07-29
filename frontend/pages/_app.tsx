import type { AppProps } from 'next/app';
import Head from 'next/head';
import { AuthProvider } from '../lib/auth';
import ErrorBoundary from '../components/ErrorBoundary';
import '../styles/globals.css';

export default function App({ Component, pageProps }: AppProps) {
  return (
    <ErrorBoundary>
      <Head>
        <title>Gatekeeper | Visitor Management</title>
        <meta name="description" content="Secure visitor management across WTC, Jayanagar and Noida locations." />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <AuthProvider>
        <Component {...pageProps} />
      </AuthProvider>
    </ErrorBoundary>
  );
}

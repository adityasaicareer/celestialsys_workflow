import Head from 'next/head';
import { useEffect, useState } from 'react';
import PostCard from '../../components/PostCard';
import Loading from '../../components/Loading';
import { fetchPosts } from '../../lib/api';
import type { Post } from '../../lib/types';

export default function Posts(): JSX.Element {
  const [posts, setPosts] = useState<Post[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState('');
  useEffect(() => { fetchPosts().then(setPosts).catch(() => setError('Unable to load posts right now.')).finally(() => setLoading(false)); }, []);
  return <>
  <Head><title>All stories | Field Notes</title></Head>
  <main className="shell py-14 sm:py-20"><p className="eyebrow">The archive</p><h1 className="mb-4">All stories</h1><p className="mb-12 max-w-xl text-slate-600">Ideas, lessons, and observations from our writers.</p>{loading ? <Loading label="Loading stories" /> : error ? <div className="notice error" role="alert">{error}</div> : posts.length ? <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">{posts.map(post => <PostCard key={post.id} post={post} />)}</div> : <div className="empty">No stories have been published yet.</div>}</main></>;
}

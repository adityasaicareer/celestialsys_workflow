import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import Layout from '../../../components/Layout';
import PostForm from '../../../components/PostForm';
import Loading from '../../../components/Loading';
import { getPost, updatePost, Post, PostInput } from '../../../lib/api';

export default function EditPost(): JSX.Element { const router = useRouter(); const [post, setPost] = useState<Post | null>(null); const [error, setError] = useState(''); useEffect(() => { if (!router.query.id) return; getPost(String(router.query.id)).then(setPost).catch(() => setError('Post could not be found.')); }, [router.query.id]); if (error) return <Layout><main className="shell state error-state">{error}</main></Layout>; if (!post) return <Loading label="Loading post" />; const submit = async (data: PostInput) => { await updatePost(post.id, data); router.push('/admin'); }; return <Layout><main className="shell admin"><p className="eyebrow">WORKSPACE / EDIT</p><h1>Edit post</h1><PostForm initial={post} onSubmit={submit} /></main></Layout>; }

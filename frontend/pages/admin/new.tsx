import PostForm from '../../components/PostForm';
import Layout from '../../components/Layout';
import { createPost, PostInput } from '../../lib/api';
import { useRouter } from 'next/router';

export default function NewPost(): JSX.Element { const router = useRouter(); const submit = async (data: PostInput) => { await createPost(data); router.push('/admin'); }; return <Layout><main className="shell admin"><p className="eyebrow">WORKSPACE / NEW</p><h1>Create a post</h1><PostForm onSubmit={submit} /></main></Layout>; }

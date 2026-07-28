import type { GetServerSideProps, InferGetServerSidePropsType } from 'next';
import Head from 'next/head';
import Link from 'next/link';
import Header from '../../components/Header';
import { fetchPost } from '../../lib/api';
import type { Post } from '../../lib/types';

export const getServerSideProps: GetServerSideProps<{ post: Post | null }> = async (context) => { try { const post = await fetchPost(String(context.params?.id)); return { props: { post } }; } catch { return { props: { post: null }, notFound: true }; } };
export default function PostPage({ post }: InferGetServerSidePropsType<typeof getServerSideProps>): JSX.Element {
  if (!post) return <><Header /><main className="container state"><h1>Story not found</h1><Link className="text-link" href="/">Return home</Link></main></>;
  return <><Head><title>{post.title} — Northstar Journal</title><meta name="description" content={post.excerpt} /></Head><Header /><main className="article-page"><article className="article"><Link className="back-link" href="/">← Back to stories</Link><span className="eyebrow">{post.category || 'Journal'} · {new Date(post.publishedAt || post.createdAt).toLocaleDateString()}</span><h1>{post.title}</h1><p className="article-lede">{post.excerpt}</p>{post.imageUrl && <img className="article-image" src={post.imageUrl} alt="" />}{post.content.split('\n').map((paragraph, index) => <p key={index}>{paragraph}</p>)}</article></main></>;
}

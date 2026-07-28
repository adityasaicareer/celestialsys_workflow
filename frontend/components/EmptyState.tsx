import Link from 'next/link';
export default function EmptyState(): JSX.Element { return <div className="state panel"><h3>Nothing here yet</h3><p>The next great story is waiting to be written.</p><Link className="text-link" href="/admin/new">Write a post →</Link></div>; }

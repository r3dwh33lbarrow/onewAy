import MainSkeleton from "./MainSkeleton.tsx";

interface ClientPageProps {
  username: string;
}

export default function ClientPage({ username }: ClientPageProps) {
  const clientPageContents = <div>Hello World</div>
  return <MainSkeleton baseName={"Client " + username} baseContents={clientPageContents} />;
}
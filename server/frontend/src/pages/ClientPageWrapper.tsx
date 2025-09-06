import { useParams } from "react-router-dom";
import ClientPage from "./ClientPage.tsx";

export default function ClientPageWrapper() {
  const { username } = useParams<{ username: string }>();

  if (!username) {
    return <div>No username provided</div>;
  }

  return <ClientPage username={username} />;
}
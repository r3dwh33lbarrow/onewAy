import { useParams } from "react-router-dom";

import ConsolePage from "./ConsolePage";

export default function ConsolePageWrapper() {
  const { username } = useParams<{ username: string }>();

  if (!username) {
    return <div>No username provided</div>;
  }

  return <ConsolePage username={username} />;
}

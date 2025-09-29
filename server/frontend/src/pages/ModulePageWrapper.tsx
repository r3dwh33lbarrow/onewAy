import { useParams } from "react-router-dom";

import ModulePage from "./ModulePage";

export default function ModulePageWrapper() {
  const { name } = useParams<{ name: string }>();

  if (!name) {
    return <div>No module name provided</div>;
  }

  return <ModulePage name={name} />;
}

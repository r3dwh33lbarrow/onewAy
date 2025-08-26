import TopBar from "./TopBar.tsx";
import MainSidebar from "./MainSidebar.tsx";

export default function Dashboard() {
  return (
    <div className="flex flex-col h-screen">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        <MainSidebar />
      </div>
    </div>
  )
}
import {
  Sidebar,
  SidebarItems,
  SidebarItemGroup,
  SidebarItem,
} from "flowbite-react";
import { HiOutlineViewGrid } from "react-icons/hi";
import { HiMiniBeaker, HiOutlineCube } from "react-icons/hi2";

type Props = { onNavigate?: () => void };

export default function MainSidebar({ onNavigate }: Props) {
  return (
    <Sidebar aria-label="Main sidebar">
      <div className="flex items-center justify-center pb-4 pr-4 pl-4">
        <img src="/onewAy_logo.png" alt="onewAy logo" className="h-10 w-auto" />
        <p className="ml-3 text-3xl">onewAy</p>
      </div>
      <hr className="border-t border-gray-300 mb-3" />

      <SidebarItems>
        <SidebarItemGroup>
          <SidebarItem
            href="/dashboard"
            icon={HiOutlineViewGrid}
            onClick={onNavigate}
          >
            Dashboard
          </SidebarItem>

          <SidebarItem
            href="/modules"
            icon={HiOutlineCube}
            onClick={onNavigate}
          >
            Modules
          </SidebarItem>

          <SidebarItem
            href="/client-builder"
            icon={HiMiniBeaker}
            onClick={onNavigate}
          >
            Client Builder
          </SidebarItem>
        </SidebarItemGroup>
      </SidebarItems>
    </Sidebar>
  );
}

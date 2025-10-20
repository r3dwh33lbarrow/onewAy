import {
  Sidebar,
  SidebarItems,
  SidebarItemGroup,
  SidebarItem,
} from "flowbite-react";
import { HiOutlineViewGrid } from "react-icons/hi";
import { HiMiniBeaker, HiOutlineCube } from "react-icons/hi2";

import { customSidebarTheme } from "../themes/sidebarTheme";

type Props = { onNavigate?: () => void };

export default function MainSidebar({ onNavigate }: Props) {
  return (
    <Sidebar aria-label="Main sidebar" theme={customSidebarTheme}>
      <div className="flex items-center justify-center pb-2 pr-4 pl-4">
        <img src="/onewAy_logo.png" alt="onewAy logo" className="h-10 w-auto" />
        <p className="ml-3 text-3xl dark:text-white">onewAy</p>
      </div>
      <hr className="border-t border-gray-400 dark:border-gray-700 mb-2.5 mt-[3px]" />

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

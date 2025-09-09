import {
  Sidebar,
  SidebarItems,
  SidebarItemGroup,
  SidebarItem,
  SidebarLogo,
} from "flowbite-react";
import { HiOutlineViewGrid } from "react-icons/hi";
import { HiOutlineCube } from "react-icons/hi2";

type Props = { onNavigate?: () => void };

export default function MainSidebar({ onNavigate }: Props) {
  return (
    <Sidebar aria-label="Main sidebar">
      <SidebarLogo
        href="/dashboard"
        img="/onewAy_logo.ico"
        imgAlt="onewAy Logo"
      >
        onewAy
      </SidebarLogo>

      <SidebarItems>
        <SidebarItemGroup>
          <SidebarItem href="/dashboard" icon={HiOutlineViewGrid} onClick={onNavigate}>
            Dashboard
          </SidebarItem>

          <SidebarItem href="/modules" icon={HiOutlineCube} onClick={onNavigate}>
            Modules
          </SidebarItem>
        </SidebarItemGroup>
      </SidebarItems>
    </Sidebar>
  );
}

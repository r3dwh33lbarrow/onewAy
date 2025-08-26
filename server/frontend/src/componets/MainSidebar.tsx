import {Sidebar, SidebarItems, SidebarItemGroup, SidebarItem, SidebarLogo} from "flowbite-react";
import { HiOutlineViewGrid } from "react-icons/hi";

type Props = { onNavigate?: () => void };

export default function MainSidebar({ onNavigate }: Props) {
  return (
    <Sidebar aria-label="Main sidebar">
      <SidebarLogo
        href="#"
        img="/onewAy_logo.webp"
        imgAlt="onewAy Logo"
      >
        onewAy
      </SidebarLogo>

      <SidebarItems>
        <SidebarItemGroup>
          <SidebarItem href="#" icon={HiOutlineViewGrid} onClick={onNavigate}>
            Dashboard
          </SidebarItem>
        </SidebarItemGroup>
      </SidebarItems>
    </Sidebar>
  );
}

import { Avatar, Dropdown, DropdownItem, DropdownHeader, DropdownDivider, Button } from "flowbite-react";
import { HiOutlineCog, HiOutlineBell } from "react-icons/hi";

export default function TopIcons() {
  return (
    <div className="flex items-center gap-3">
      <Button color="gray" pill size="sm" aria-label="Notifications">
        <HiOutlineBell className="h-5 w-5" />
      </Button>

      <Button color="gray" pill size="sm" aria-label="Settings">
        <HiOutlineCog className="h-5 w-5" />
      </Button>

      <Dropdown
        inline
        label={<Avatar rounded alt="User avatar" />}
      >
        <DropdownHeader>
          <span className="block text-sm">John Doe</span>
        </DropdownHeader>
        <DropdownItem>Profile</DropdownItem>
        <DropdownItem>Settings</DropdownItem>
        <DropdownDivider />
        <DropdownItem>Sign out</DropdownItem>
      </Dropdown>
    </div>
  );
}

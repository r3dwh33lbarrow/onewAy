import { Avatar, Dropdown, DropdownItem, DropdownHeader, DropdownDivider, Button } from "flowbite-react";
import { HiOutlineCog, HiOutlineBell } from "react-icons/hi";
import {useNavigate} from "react-router-dom";

const customDropdownTheme = {
  "arrowIcon": "ml-2 h-4 w-4 dark:fill-gray-200",
  "content": "py-1 focus:outline-none",
  "floating": {
    "animation": "transition-opacity",
    "arrow": {
      "base": "absolute z-10 h-2 w-2 rotate-45",
      "style": {
        "dark": "bg-gray-900 dark:bg-gray-700",
        "light": "bg-white",
        "auto": "bg-white dark:bg-gray-700"
      },
      "placement": "-4px"
    },
    "base": "z-10 w-fit divide-y divide-gray-100 rounded shadow focus:outline-none",
    "content": "py-1 text-sm text-gray-700 dark:text-gray-200",
    "divider": "my-1 h-px bg-gray-100 dark:bg-gray-600",
    "header": "block px-4 py-2 text-sm text-gray-700 dark:text-gray-200",
    "hidden": "invisible opacity-0",
    "item": {
      "container": "",
      "base": "flex w-full cursor-pointer items-center justify-start px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 focus:bg-gray-100 focus:outline-none dark:text-gray-200 dark:hover:bg-gray-600 dark:hover:text-white dark:focus:bg-gray-600 dark:focus:text-white",
      "icon": "mr-2 h-4 w-4"
    },
    "style": {
      "dark": "bg-gray-900 text-white dark:bg-gray-700",
      "light": "border border-gray-200 bg-white text-gray-900",
      "auto": "border border-gray-200 bg-white text-gray-900 dark:border-none dark:bg-gray-700 dark:text-white"
    },
    "target": "w-fit"
  },
  "inlineWrapper": "flex items-center"
};

export default function TopIcons() {
  const navigate = useNavigate();

  return (
    <div className="flex items-center gap-3">
      <Button color="gray" pill size="sm" aria-label="Notifications">
        <HiOutlineBell className="h-5 w-5" />
      </Button>

      <Button onClick={() => navigate("/settings")} color="gray" pill size="sm" aria-label="Settings">
        <HiOutlineCog className="h-5 w-5" />
      </Button>

      <Dropdown
        inline
        label={<Avatar rounded alt="User avatar" />}
        theme={customDropdownTheme}
      >
        <DropdownHeader>
          <span className="block text-sm">John Doe</span>
        </DropdownHeader>
        <DropdownItem>Profile</DropdownItem>
        <DropdownDivider />
        <DropdownItem>Sign out</DropdownItem>
      </Dropdown>
    </div>
  );
}

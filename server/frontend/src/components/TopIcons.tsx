import { Avatar, Dropdown, DropdownItem, DropdownHeader, DropdownDivider, Button } from "flowbite-react";
import { HiOutlineCog, HiOutlineBell } from "react-icons/hi";
import {useNavigate} from "react-router-dom";
import {useEffect} from "react";
import {useAvatarStore} from "../stores/useAvatarStore.ts";

export default function TopIcons() {
  const navigate = useNavigate();
  const { avatarUrl, fetchAvatar } = useAvatarStore();

  useEffect(() => {
    if (!avatarUrl) {
      fetchAvatar();
    }
  }, [avatarUrl, fetchAvatar]);

  return (
    <div className="flex items-center gap-3">
      <Button color="gray" pill size="sm" aria-label="Notifications">
        <HiOutlineBell className="h-5 w-5" />
      </Button>

      <Button
        onClick={() => navigate("/settings")}
        color="gray"
        pill
        size="sm"
        aria-label="Settings"
      >
        <HiOutlineCog className="h-5 w-5" />
      </Button>

      <Dropdown
        inline
        label={
          <Avatar
            rounded
            alt="User avatar"
            img={avatarUrl ?? undefined}
          />
        }
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

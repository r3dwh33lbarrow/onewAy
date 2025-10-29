import { Avatar, Dropdown, DropdownItem, Button } from "flowbite-react";
import { useEffect, useRef, useState } from "react";
import { HiOutlineCog, HiOutlineBell } from "react-icons/hi";
import { useNavigate } from "react-router-dom";

import { apiClient } from "../apiClient";
import { useAuthStore } from "../stores/authStore";
import { useNotificationStore } from "../stores/notificationStore.ts";
import { useAvatarStore } from "../stores/useAvatarStore";
import { customDropdownTheme } from "../themes/dropdownTheme";

export default function TopIcons() {
  const navigate = useNavigate();
  const { avatarUrl, fetchAvatar } = useAvatarStore();
  const notifications = useNotificationStore((state) => state.notifications);
  const hasUnread = useNotificationStore((state) => state.hasUnread);
  const query = useNotificationStore((state) => state.query);
  const clearUser = useAuthStore((state) => state.clearUser);
  const clearAvatar = useAvatarStore((state) => state.clearAvatar);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const notificationButtonRef = useRef<HTMLButtonElement | null>(null);
  const notificationPanelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!avatarUrl) {
      fetchAvatar();
    }
  }, [avatarUrl, fetchAvatar]);

  useEffect(() => {
    query();
  }, [query]);

  const handleLogout = async () => {
    await apiClient.post<object, { result: string }>("/user/auth/logout", {});
    clearUser();
    clearAvatar();
    navigate("/login");
  };

  useEffect(() => {
    if (!notificationsOpen) return;

    const onClick = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        notificationPanelRef.current &&
        !notificationPanelRef.current.contains(target) &&
        notificationButtonRef.current &&
        !notificationButtonRef.current.contains(target)
      ) {
        setNotificationsOpen(false);
      }
    };

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setNotificationsOpen(false);
    };

    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [notificationsOpen]);

  return (
    <div className="flex items-center gap-3">
      <div className="relative">
        <Button
          ref={notificationButtonRef}
          color="gray"
          pill
          size="sm"
          aria-label="Notifications"
          onClick={() => setNotificationsOpen((v) => !v)}
          className="relative"
        >
          <HiOutlineBell className="h-5 w-5" />
          {hasUnread && (
            <span className="absolute -top-0.5 -right-0.5 inline-flex h-3 w-3 rounded-full bg-red-500" />
          )}
        </Button>

        {notificationsOpen && (
          <div
            ref={notificationPanelRef}
            className="absolute right-0 mt-2 w-72 z-40"
          >
            <div className="relative">
              <div className="absolute right-4 -top-0.5 h-3 w-3 rotate-45 bg-white border-l border-t border-gray-200 dark:bg-gray-700 dark:border-gray-600"></div>
              <div className="rounded-lg border border-gray-200 bg-white shadow-md dark:border-gray-600 dark:bg-gray-700 overflow-hidden">
                {notifications.length === 0 ? (
                  <div className="p-3 text-sm text-gray-500 dark:text-gray-300">
                    No notifications
                  </div>
                ) : (
                  <div className="max-h-96 overflow-y-auto">
                    {notifications.map((bucket_info) => {
                      const isUnread = !bucket_info.consumed;
                      const createdAtDate = new Date(bucket_info.created_at);
                      const createdAtLabel = Number.isNaN(
                        createdAtDate.getTime(),
                      )
                        ? bucket_info.created_at
                        : createdAtDate.toLocaleString();
                      const clientLabel =
                        bucket_info.client_username ?? "Unassigned client";
                      return (
                        <div
                          key={`${bucket_info.name}-${bucket_info.entry_uuid ?? "none"}`}
                          className="p-3 border-b border-gray-200 dark:border-gray-600 last:border-b-0 hover:bg-gray-50 dark:hover:bg-gray-600 cursor-pointer"
                          onClick={() => {
                            const targetPath = bucket_info.entry_uuid
                              ? `/bucket/${bucket_info.name}?entry=${encodeURIComponent(bucket_info.entry_uuid)}`
                              : `/bucket/${bucket_info.name}`;
                            navigate(targetPath);
                            setNotificationsOpen(false);
                          }}
                        >
                          <div className="flex items-center gap-2">
                            {isUnread && (
                              <span className="inline-flex h-2 w-2 rounded-full bg-red-500" />
                            )}
                            <div className="text-sm font-medium text-gray-900 dark:text-white">
                              {bucket_info.name + " - " + clientLabel}
                            </div>
                          </div>
                          <div className="text-xs text-gray-600 dark:text-gray-300 mt-1">
                            {`Created at: ${createdAtLabel}`}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

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
          <Avatar rounded alt="User avatar" img={avatarUrl ?? undefined} />
        }
        theme={customDropdownTheme}
      >
        <DropdownItem onClick={handleLogout}>Sign out</DropdownItem>
      </Dropdown>
    </div>
  );
}

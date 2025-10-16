import { Avatar, Dropdown, DropdownItem, Button } from "flowbite-react";
import { useEffect, useRef, useState } from "react";
import { HiOutlineCog, HiOutlineBell } from "react-icons/hi";
import { useNavigate } from "react-router-dom";

import {apiClient, isApiError} from "../apiClient";
import { useAuthStore } from "../stores/authStore";
import { useAvatarStore } from "../stores/useAvatarStore";
import type {AllBucketsResponse} from "../schemas/module_bucket.ts";

const customDropdownTheme = {
  arrowIcon: "ml-2 h-4 w-4 dark:fill-gray-200",
  content: "py-1 focus:outline-none",
  floating: {
    animation: "transition-opacity",
    arrow: {
      base: "absolute z-10 h-2 w-2 rotate-45",
      style: {
        dark: "bg-gray-900 dark:bg-gray-700",
        light: "bg-white",
        auto: "bg-white dark:bg-gray-700",
      },
      placement: "-4px",
    },
    base: "z-10 w-fit divide-y divide-gray-100 rounded shadow focus:outline-none",
    content: "py-1 text-sm text-gray-700 dark:text-gray-200",
    divider: "my-1 h-px bg-gray-100 dark:bg-gray-600",
    header: "block px-4 py-2 text-sm text-gray-700 dark:text-gray-200",
    hidden: "invisible opacity-0",
    item: {
      container: "",
      base: "flex w-full cursor-pointer items-center justify-start px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 focus:bg-gray-100 focus:outline-none dark:text-gray-200 dark:hover:bg-gray-600 dark:hover:text-white dark:focus:bg-gray-600 dark:focus:text-white",
      icon: "mr-2 h-4 w-4",
    },
    style: {
      dark: "bg-gray-900 text-white dark:bg-gray-700",
      light: "border border-gray-200 bg-white text-gray-900",
      auto: "border border-gray-200 bg-white text-gray-900 dark:border-none dark:bg-gray-700 dark:text-white",
    },
    target: "w-fit",
  },
  inlineWrapper: "flex items-center",
};

export default function TopIcons() {
  const navigate = useNavigate();
  const { avatarUrl, fetchAvatar } = useAvatarStore();
  const clearUser = useAuthStore((state) => state.clearUser);
  const clearAvatar = useAvatarStore((state) => state.clearAvatar);
  const [notifOpen, setNotifOpen] = useState(false);
  const [notifications, setNotifications] = useState<Record<string, string[]>>(
    {},
  );
  const notifBtnRef = useRef<HTMLButtonElement | null>(null);
  const notifPanelRef = useRef<HTMLDivElement | null>(null);

  // Check if there are any "not consumed" notifications
  const hasUnread = Object.values(notifications).some((messages) =>
    messages.some((msg) => msg === "not consumed")
  );

  useEffect(() => {
    if (!avatarUrl) {
      fetchAvatar();
    }
  }, [avatarUrl, fetchAvatar]);

  useEffect(() => {
    const getAllBuckets = async () => {
      const response = await apiClient.get<AllBucketsResponse>(
        "/module/all-buckets",
      );

      if (!isApiError(response)) {
        for (const [module, consumed] of Object.entries(response.buckets)) {
          setNotifications((prev) => ({
            ...prev,
            [module]: [consumed],
          }));
        }
      }
    };

    getAllBuckets();
  }, []);

  const handleLogout = async () => {
    await apiClient.post<object, { result: string }>("/user/auth/logout", {});
    clearUser();
    clearAvatar();
    navigate("/login");
  };

  useEffect(() => {
    if (!notifOpen) return;

    const onClick = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        notifPanelRef.current &&
        !notifPanelRef.current.contains(target) &&
        notifBtnRef.current &&
        !notifBtnRef.current.contains(target)
      ) {
        setNotifOpen(false);
      }
    };

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setNotifOpen(false);
    };

    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [notifOpen]);

  return (
    <div className="flex items-center gap-3">
      <div className="relative">
        <Button
          ref={notifBtnRef}
          color="gray"
          pill
          size="sm"
          aria-label="Notifications"
          onClick={() => setNotifOpen((v) => !v)}
          className="relative"
        >
          <HiOutlineBell className="h-5 w-5" />
          {hasUnread && (
            <span className="absolute -top-0.5 -right-0.5 inline-flex h-3 w-3 rounded-full bg-red-500" />
          )}
        </Button>

        {notifOpen && (
          <div
            ref={notifPanelRef}
            className="absolute right-0 mt-2 w-72 z-40"
          >
            {/* Arrow */}
            <div className="relative">
              <div className="absolute right-4 -top-0.5 h-3 w-3 rotate-45 bg-white border-l border-t border-gray-200 dark:bg-gray-700 dark:border-gray-600"></div>
              <div className="rounded-lg border border-gray-200 bg-white shadow-md dark:border-gray-600 dark:bg-gray-700 overflow-hidden">
                {Object.keys(notifications).length === 0 ? (
                  <div className="p-3 text-sm text-gray-500 dark:text-gray-300">
                    No notifications
                  </div>
                ) : (
                  <div className="max-h-96 overflow-y-auto">
                    {Object.entries(notifications).map(([module, messages]) => {
                      const isUnread = messages.some((msg) => msg === "not consumed");
                      return (
                        <div
                          key={module}
                          className="p-3 border-b border-gray-200 dark:border-gray-600 last:border-b-0 hover:bg-gray-50 dark:hover:bg-gray-600 cursor-pointer"
                          onClick={() => {
                            navigate(`/bucket/${module}`);
                            setNotifOpen(false);
                          }}
                        >
                          <div className="flex items-center gap-2">
                            {isUnread && (
                              <span className="inline-flex h-2 w-2 rounded-full bg-red-500" />
                            )}
                            <div className="text-sm font-medium text-gray-900 dark:text-white">
                              {module}
                            </div>
                          </div>
                          {messages.map((msg, idx) => (
                            <div
                              key={idx}
                              className="text-xs text-gray-600 dark:text-gray-300 mt-1"
                            >
                              {msg}
                            </div>
                          ))}
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

import { Card } from "flowbite-react";
import { HiOutlineDesktopComputer } from "react-icons/hi";

import type { BasicClientInfo } from "../schemas/client";

export default function ClientCard({
  username,
  hostname,
  alive,
  last_contact,
}: BasicClientInfo) {
  return (
    <Card
      className="w-full col-span-full dark:text-white"
      href={`/client/${username}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex flex-col items-center">
          <HiOutlineDesktopComputer className="text-2xl mb-1" />
          <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
            {username}
          </p>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex flex-col text-right">
            <p className="text-sm">{hostname ? hostname : "N/A"}</p>
            <p className="text-xs text-gray-500">
              {last_contact ? last_contact : "N/A"}
            </p>
          </div>
          <div
            className={`w-4 h-4 rounded-full ${alive ? "bg-green-500" : "bg-red-500"}`}
          ></div>
        </div>
      </div>
    </Card>
  );
}

import { Avatar } from "flowbite-react";

export default function TopBar() {
  return (
    <header className="flex p-2 justify-between items-center dark:bg-gray-800 dark:text-gray-300">
      <h1 className="text-2xl font-bold ml-4">onewAy</h1>
      <Avatar className="mr-4" rounded />
    </header>
  )
}
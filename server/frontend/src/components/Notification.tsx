import {Card} from "flowbite-react";

interface NotificationProps {
  name: string;
  read: boolean;
}


export default function Notification([{ name: string, read: boolean }]: NotificationProps[]) {
  return (
    <Card>Hi</Card>
  );
}
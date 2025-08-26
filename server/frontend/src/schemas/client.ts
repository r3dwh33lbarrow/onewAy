export interface BasicClientInfo {
  username: string;
  ip_address: string;
  hostname: string;
  alive: boolean;
  last_contact: string;
}

export interface ClientAllResponse {
  clients: BasicClientInfo[];
}
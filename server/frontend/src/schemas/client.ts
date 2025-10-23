export interface BasicClientInfo {
  username: string;
  ip_address: string;
  hostname: string;
  alive: boolean;
  last_contact: string;
  platform?: string | null;
}

export interface ClientAllResponse {
  clients: BasicClientInfo[];
}

export interface ClientInfo extends BasicClientInfo {
  uuid: string;
  client_version: string;
  any_valid_tokens: boolean;
}

export interface ClientAllInfo {
  uuid: string;
  username: string;
  ip_address: string;
  hostname: string;
  alive: boolean;
  last_contact: string;
  client_version: string;
  any_valid_tokens: boolean;
}

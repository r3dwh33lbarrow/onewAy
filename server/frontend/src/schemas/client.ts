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

export interface ClientInfo extends BasicClientInfo {
  uuid: string;
  last_known_location: string;
  any_valid_tokens: boolean;
}

export interface ClientAllInfo {
  uuid: string;
  username: string;
  ip_address: string;
  hostname: string;
  alive: boolean;
  last_contact: string;
  last_known_location: string;
  client_version: string;
}

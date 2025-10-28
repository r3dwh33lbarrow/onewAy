export interface BucketInfo {
  name: string;
  consumed: boolean;
  created_at: string;
  client_username: string | null;
  entry_uuid: string | null;
}

export interface BucketEntry {
  uuid: string;
  client_username: string | null;
  data: string;
  consumed: boolean;
  created_at: string;
  remove_at: string | null;
}

export interface ModuleBucketResponse {
  module_name: string;
  entries: BucketEntry[];
}

export interface AllBucketsResponse {
  buckets: BucketInfo[];
}

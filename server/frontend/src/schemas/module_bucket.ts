export interface BucketData {
  data: string;
}

export interface BucketInfo {
  name: string;
  consumed: boolean;
  created_at: string;
}

export interface AllBucketsResponse {
  buckets: BucketInfo[];
}

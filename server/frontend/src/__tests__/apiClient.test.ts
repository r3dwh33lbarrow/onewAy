import { apiClient } from "../apiClient";

const API_URL = "http://localhost:8000/";
const TIMEOUT = 10000;

describe('ApiClient - Live API Tests', () => {
  beforeAll(async () => {
    console.log(`Testing against API: ${API_URL}`);
  }, TIMEOUT);

  describe('setApiUrl', () => {

  })
})
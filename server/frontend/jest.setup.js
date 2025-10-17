const { fetch, Headers, Request, Response } = require('undici');

// Provide missing globals that undici needs
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

global.fetch = fetch;
global.Headers = Headers;
global.Request = Request;
global.Response = Response;

// Mock localStorage for Zustand persist middleware with actual storage functionality
const createLocalStorageMock = () => {
  let store = {};

  return {
    getItem: jest.fn((key) => store[key] || null),
    setItem: jest.fn((key, value) => {
      store[key] = value.toString();
    }),
    removeItem: jest.fn((key) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: jest.fn((index) => {
      const keys = Object.keys(store);
      return keys[index] || null;
    }),
  };
};

const localStorageMock = createLocalStorageMock();
global.localStorage = localStorageMock;
global.Storage = jest.fn(() => localStorageMock);

import { Alert, Button, Label, TextInput } from "flowbite-react";
import React, { useState, useEffect } from "react";
import { HiMiniExclamationCircle, HiInformationCircle } from "react-icons/hi2";
import { useLocation, useNavigate } from "react-router-dom";

import { apiClient, type ApiError, isApiError } from "../apiClient";
import ApiUrlInput from "./ApiUrlInput";
import type { AuthRequest } from "../schemas/authentication.ts";
import type { BasicTaskResponse } from "../schemas/general.ts";
import { useAuthStore } from "../stores/authStore";
import { useRedirectReasonStore } from "../stores/redirectReasonStore";

interface LoginPanelProps {
  onSubmit: (data: AuthRequest) => Promise<BasicTaskResponse | ApiError>;
}

export default function LoginPanel({ onSubmit }: LoginPanelProps) {
  const navigate = useNavigate();
  const location = useLocation();

  const [apiUrl, setApiUrl] = useState(
    apiClient.getApiUrl() ?? "http://localhost:8000/",
  );
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    username: "",
    password: "",
  });

  const setUser = useAuthStore((state) => state.setUser);
  const redirectReason = useRedirectReasonStore((state) => state.reason);
  const clearRedirectReason = useRedirectReasonStore(
    (state) => state.clearReason,
  );

  // Display redirect reason and clear it
  useEffect(() => {
    if (redirectReason) {
      // Clear the reason after a delay to allow user to see it
      const timer = setTimeout(() => {
        clearRedirectReason();
      }, 10000); // Clear after 10 seconds

      return () => clearTimeout(timer);
    }
  }, [redirectReason, clearRedirectReason]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { id, value } = e.target;
    setFormData((prevFormData) => ({
      ...prevFormData,
      [id]: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    const isUrlValid = await apiClient.setApiUrl(apiUrl);
    if (isUrlValid) {
      const response = await onSubmit(formData);
      if (!isApiError(response)) {
        setUser({ username: formData.username });
        const from = location.state?.from?.pathname || "/dashboard";
        navigate(from, { replace: true });
      } else {
        setError(`${response.message}: ${response.detail}`);
      }
    } else {
      setError("Invalid API URL");
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
      <div className="fixed top-4 left-1/2 transform -translate-x-1/2 w-3/4 px-4 z-50">
        {redirectReason && (
          <Alert
            icon={HiInformationCircle}
            color="warning"
            className="mb-4 w-full"
            onDismiss={clearRedirectReason}
          >
            <span>{redirectReason}</span>
          </Alert>
        )}
        {error && (
          <Alert
            icon={HiMiniExclamationCircle}
            color="failure"
            className="mb-4 w-full"
            onDismiss={() => setError(null)}
          >
            <span>{error}</span>
          </Alert>
        )}
      </div>

      <div className="w-full max-w-md rounded-lg shadow-xl flex flex-col items-center justify-center p-6 bg-white dark:bg-gray-800">
        <h1 className="text-xl font-bold dark:text-white mb-4">onewAy Login</h1>

        <ApiUrlInput
          value={apiUrl}
          onChange={setApiUrl}
          onValidationChange={() => {}}
        />

        <form className="flex flex-col gap-4 w-full" onSubmit={handleSubmit}>
          <div>
            <div className="mt-2 mb-2 block">
              <Label htmlFor="username">Username</Label>
            </div>
            <TextInput
              id="username"
              type="text"
              placeholder="Username"
              required={true}
              value={formData.username}
              onChange={handleChange}
            />
          </div>

          <div>
            <div className="mb-2 block">
              <Label htmlFor="password">Password</Label>
            </div>
            <TextInput
              id="password"
              type="password"
              placeholder="Password"
              required={true}
              value={formData.password}
              onChange={handleChange}
            />
          </div>

          <div className="flex items-center w-full mt-2">
            <Button color="indigo" type="submit" className="w-full">
              Login
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

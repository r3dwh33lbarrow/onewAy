import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Alert, Button, Label, TextInput } from "flowbite-react";
import { apiClient } from "../apiClient.ts";
import ApiUrlInput from "./ApiUrlInput.tsx";
import { useAuthStore } from "../stores/authStore.ts";

interface AuthFormProps {
  title: string;
  submitButtonText: string;
  onSubmit: (data: { username: string; password: string }) => Promise<boolean>;
  successRedirectPath: string;
  errorMessage: string;
  footerText: string;
  footerLinkText: string;
  footerLinkPath: string;
}

export default function AuthForm({
  title,
  submitButtonText,
  onSubmit,
  successRedirectPath,
  errorMessage,
  footerText,
  footerLinkText,
  footerLinkPath,
}: AuthFormProps) {
  const navigate = useNavigate();
  const location = useLocation();

  const [apiUrl, setApiUrl] = useState('http://localhost:8000');
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });

  const setUser = useAuthStore(state => state.setUser);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { id, value } = e.target;
    setFormData(prevFormData => ({
      ...prevFormData,
      [id]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    const isUrlValid = await apiClient.setApiUrl(apiUrl);
    if (isUrlValid) {
      const success = await onSubmit(formData);
      if (success) {
        if (successRedirectPath === '/dashboard') {
          setUser({ username: formData.username });
          const from = location.state?.from?.pathname || '/dashboard';
          navigate(from, { replace: true });
        } else {
          navigate(successRedirectPath);
        }
      } else {
        setError(errorMessage);
      }
    } else {
      setError('Invalid API URL');
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
      <div className="w-full max-w-md rounded-lg shadow-xl flex flex-col items-center justify-center p-6 bg-white dark:bg-gray-800">
        <h1 className="text-xl font-bold dark:text-white mb-4">{title}</h1>

        {error && (
          <Alert color="failure" className="mb-4 w-full" onDismiss={() => setError(null)}>
            <span>{error}</span>
          </Alert>
        )}

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
              {submitButtonText}
            </Button>
          </div>
        </form>

        <div className="mt-4 text-center text-sm text-gray-600 dark:text-gray-400">
          {footerText}{' '}
          <span
            className="text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer"
            onClick={() => navigate(footerLinkPath)}
          >
            {footerLinkText}
          </span>
        </div>
      </div>
    </div>
  );
}

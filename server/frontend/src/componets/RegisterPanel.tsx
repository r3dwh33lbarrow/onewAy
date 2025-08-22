import {useNavigate} from "react-router-dom";
import React, {useState} from "react";
import {apiClient} from "../apiClient.ts";
import {Alert, Button, Label, TextInput} from "flowbite-react";

interface RegisterPanelProps {
  onSubmit: (data: { username: string, password: string }) => Promise<boolean>;
}

export default function RegisterPanel({ onSubmit }: RegisterPanelProps) {
  const navigate = useNavigate();

  const [apiUrl, setApiUrl] = useState('http://localhost:8000');
  const [registerError, setRegisterError] = useState<string | null>(null);
  const [urlValidation, setUrlValidation] = useState<'valid' | 'invalid' | 'pending'>('pending');
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });

  const handleApiUrlChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const { value } = e.target;
    setApiUrl(value);
  };

  const handleApiUrlBlur = async () => {
    setUrlValidation('pending');
    const isUrlValid = await apiClient.setApiUrl(apiUrl);
    setUrlValidation(isUrlValid ? 'valid' : 'invalid');
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { id, value } = e.target;
    setFormData(prevFormData => ({
      ...prevFormData,
      [id]: value
    }));
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const isUrlValid = await apiClient.setApiUrl(apiUrl);
    if (isUrlValid) {
      const success = await onSubmit(formData);
      if (success) {
        navigate('/login');
      } else {
        setRegisterError('Failed to register');
      }
    }
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
      <div className="w-full max-w-md rounded-lg shadow-xl flex flex-col items-center justify-center p-6 bg-white dark:bg-gray-800">
        <h1 className="text-xl font-bold dark:text-white mb-4">onewAy Registration</h1>

        {registerError && (
          <Alert color="failure" className="mb-4 w-full" onDismiss={() => setRegisterError(null)}>
            <span>{registerError}</span>
          </Alert>
        )}

        <div className="w-full mb-2">
          <div className="mb-2 block">
            <Label htmlFor="apiUrl">API URL</Label>
          </div>

          <TextInput
            id="apiUrl"
            type="url"
            value={apiUrl}
            required={true}
            onChange={handleApiUrlChange}
            onBlur={handleApiUrlBlur}
            color={urlValidation === 'valid' ? 'success' : urlValidation === 'invalid' ? 'failure' : 'gray'}
          />
        </div>

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
            <Button color="indigo" type="submit" className="w-full">Register</Button>
          </div>
        </form>

        <div className="mt-4 text-center text-sm text-gray-600 dark:text-gray-400">
          Already have an account? <span className="text-indigo-600 dark:text-indigo-400
          hover:underline cursor-pointer" onClick={() => navigate('/login')}>
          Login</span>
        </div>
      </div>
    </div>
  )
}
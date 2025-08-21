import {apiClient} from '../apiClient';
import {useNavigate} from 'react-router-dom';
import React, {useState} from "react";
import {Alert, Button, Checkbox, Label, TextInput} from "flowbite-react";

interface LoginPanelProps {
  onSubmit: (data: { username: string, password: string, rememberMe: boolean }) => Promise<boolean>;
}

export default function LoginPanel({ onSubmit }: LoginPanelProps) {
  const navigate = useNavigate();

  const [apiUrl, setApiUrl] = useState('http://localhost:8000');
  const [LoginError, setLoginError] = useState<string | null>(null);
  const [urlValidation, setUrlValidation] = useState<'valid' | 'invalid' | 'pending'>('pending');

  const [formData, setFormData] = useState({
    username: '',
    password: '',
    rememberMe: false
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
    const { id, value, type, checked } = e.target;
    const newValue = type === 'checkbox' ? checked : value;

    setFormData(prevFormData => ({
      ...prevFormData,
      [id]: newValue
    }));
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    // Fix this: this is unnecessary
    const isUrlValid = await apiClient.setApiUrl(apiUrl);
    if (isUrlValid) {
      const authenticated = await onSubmit(formData);
      if (authenticated) {
        navigate('/dashboard');
      } else {
        setLoginError('Invalid username or password');
      }
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
      <div className="w-full max-w-md rounded-lg shadow-xl flex flex-col items-center justify-center p-6 bg-white dark:bg-gray-800">
        <h1 className="text-xl font-bold dark:text-white mb-4">onewAy</h1>

        {LoginError && (
          <Alert color="failure" className="mb-4 w-full" onDismiss={() => setLoginError(null)}>
            <span>{LoginError}</span>
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
            color={urlValidation === 'valid' ? 'sucess': urlValidation === 'invalid' ? 'failure': 'gray'}
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

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 m-2">
              <Checkbox
                id="rememberMe"
                checked={formData.rememberMe}
                onChange={handleChange}
                color="indigo"
              />

              <Label htmlFor="rememberMe">Remember Me</Label>
            </div>
          </div>

          <Button color="indigo" type="submit">Log In</Button>
        </form>

        <div className="mt-4 text-center text-sm text-gray-600 dark:text-gray-400">
          Don't have an account? <span className="text-indigo-600 dark:text-indigo-400
          hover:underline cursor-pointer" onClick={() => navigate('/register')}>Register</span>
        </div>
      </div>
    </div>
  )
}
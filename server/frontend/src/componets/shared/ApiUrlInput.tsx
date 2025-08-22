import React, { useState } from 'react';
import { Label, TextInput } from 'flowbite-react';
import { apiClient } from '../../apiClient';

interface ApiUrlInputProps {
  value: string;
  onChange: (url: string) => void;
  onValidationChange: (isValid: boolean) => void;
}

export default function ApiUrlInput({ value, onChange, onValidationChange }: ApiUrlInputProps) {
  const [urlValidation, setUrlValidation] = useState<'valid' | 'invalid' | 'pending'>('pending');

  const handleApiUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { value: newValue } = e.target;
    onChange(newValue);
  };

  const handleApiUrlBlur = async () => {
    setUrlValidation('pending');
    const isUrlValid = await apiClient.setApiUrl(value);
    setUrlValidation(isUrlValid ? 'valid' : 'invalid');
    onValidationChange(isUrlValid);
  };

  return (
    <div className="w-full mb-2">
      <div className="mb-2 block">
        <Label htmlFor="apiUrl">API URL</Label>
      </div>
      <TextInput
        id="apiUrl"
        type="url"
        value={value}
        required={true}
        onChange={handleApiUrlChange}
        onBlur={handleApiUrlBlur}
        color={urlValidation === 'valid' ? 'success' : urlValidation === 'invalid' ? 'failure' : 'gray'}
      />
    </div>
  );
}

import AuthForm from "./AuthForm";
import type { ApiError } from "../apiClient.ts";
import type { AuthRequest } from "../schemas/authentication.ts";
import type { BasicTaskResponse } from "../schemas/general.ts";

interface LoginPanelProps {
  onSubmit: (data: AuthRequest) => Promise<BasicTaskResponse | ApiError>;
}

export default function LoginPanel({ onSubmit }: LoginPanelProps) {
  return (
    <AuthForm
      title="onewAy Login"
      submitButtonText="Login"
      onSubmit={onSubmit}
      successRedirectPath="/dashboard"
      footerText="Don't have an account?"
      footerLinkText="Register"
      footerLinkPath="/register"
    />
  );
}

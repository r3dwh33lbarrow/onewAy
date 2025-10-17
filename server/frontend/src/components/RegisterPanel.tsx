import AuthForm from "./AuthForm";
import type { ApiError } from "../apiClient.ts";
import type { AuthRequest } from "../schemas/authentication.ts";
import type { BasicTaskResponse } from "../schemas/general.ts";

interface RegisterPanelProps {
  onSubmit: (data: AuthRequest) => Promise<BasicTaskResponse | ApiError>;
}

export default function RegisterPanel({ onSubmit }: RegisterPanelProps) {
  return (
    <AuthForm
      title="onewAy Registration"
      submitButtonText="Register"
      onSubmit={onSubmit}
      successRedirectPath="/login"
      footerText="Already have an account?"
      footerLinkText="Login"
      footerLinkPath="/login"
    />
  );
}

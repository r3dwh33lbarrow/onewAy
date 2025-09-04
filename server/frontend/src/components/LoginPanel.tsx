import AuthForm from "./AuthForm.tsx";

interface LoginPanelProps {
  onSubmit: (data: { username: string, password: string }) => Promise<boolean>;
}

export default function LoginPanel({ onSubmit }: LoginPanelProps) {
  return (
    <AuthForm
      title="onewAy Login"
      submitButtonText="Login"
      onSubmit={onSubmit}
      successRedirectPath="/dashboard"
      errorMessage="Invalid username or password"
      footerText="Don't have an account?"
      footerLinkText="Register"
      footerLinkPath="/register"
    />
  );
}
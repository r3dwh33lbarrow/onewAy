import AuthForm from "./shared/AuthForm";

interface RegisterPanelProps {
  onSubmit: (data: { username: string, password: string }) => Promise<boolean>;
}

export default function RegisterPanel({ onSubmit }: RegisterPanelProps) {
  return (
    <AuthForm
      title="onewAy Registration"
      submitButtonText="Register"
      onSubmit={onSubmit}
      successRedirectPath="/login"
      errorMessage="Failed to register"
      footerText="Already have an account?"
      footerLinkText="Login"
      footerLinkPath="/login"
    />
  );
}
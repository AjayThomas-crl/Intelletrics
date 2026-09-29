export type SignupValues = {
  fullName: string;
  email: string;
  password: string;
  confirmPassword: string;
};

export type SignupErrors = Partial<Record<keyof SignupValues, string>>;

export function validateSignup(values: SignupValues): SignupErrors {
  const errors: SignupErrors = {};
  const name = values.fullName.trim();
  const email = values.email.trim();
  if (name.length < 2 || name.length > 100) {
    errors.fullName = "Enter your name (2–100 characters).";
  }
  if (email.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    errors.email = "Enter a valid email address.";
  }
  if (values.password.length < 8) {
    errors.password = "Use at least 8 characters.";
  } else if (values.password.length > 128) {
    errors.password = "Use no more than 128 characters.";
  } else if (!values.password.trim()) {
    errors.password = "Your password cannot contain only spaces.";
  }
  if (!values.confirmPassword) {
    errors.confirmPassword = "Enter your password again.";
  } else if (values.password !== values.confirmPassword) {
    errors.confirmPassword = "Your passwords do not match.";
  }
  return errors;
}

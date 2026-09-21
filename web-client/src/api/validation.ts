export type ClientFieldErrors = Record<string, string>;

const allowedName = /^[A-Za-z0-9!#$%^&*()\-_=+?]+$/;
const allowedPassword = /^[A-Za-z0-9!@#$%^&*()\-_=+?]+$/;

export function validateRegistration(values: {
  username: string;
  email: string;
  password: string;
  passwordConfirmation: string;
  displayName: string;
}): ClientFieldErrors {
  const errors: ClientFieldErrors = {};
  if (!values.username || !allowedName.test(values.username)) {
    errors.username = "Use letters, digits, or ! # $ % ^ & * ( ) - _ = + ?.";
  }
  if (!/^[^\s@]+@u\.nus\.edu$/i.test(values.email.trim())) {
    errors.email = "Use your NUS student email ending in @u.nus.edu.";
  }
  if (values.displayName && !allowedName.test(values.displayName)) {
    errors.displayName = "Use letters, digits, or ! # $ % ^ & * ( ) - _ = + ?.";
  }
  if (values.password.length < 12 || values.password.length > 72 || !allowedPassword.test(values.password)) {
    errors.password = "Use 12–72 allowed characters.";
  } else {
    const groups = [/[A-Z]/, /[a-z]/, /\d/, /[!@#$%^&*()\-_=+?]/].filter((rule) =>
      rule.test(values.password),
    ).length;
    if (groups < 3) errors.password = "Use at least three: uppercase, lowercase, digits, special characters.";
  }
  if (values.password !== values.passwordConfirmation) {
    errors.passwordConfirmation = "Passwords do not match.";
  }
  return errors;
}

export function validateDisplayName(value: string): string | undefined {
  if (!value) return "Enter a display name.";
  if (!allowedName.test(value)) return "Use letters, digits, or ! # $ % ^ & * ( ) - _ = + ?.";
  return undefined;
}

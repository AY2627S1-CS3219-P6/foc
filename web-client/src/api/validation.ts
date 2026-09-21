export type ClientFieldErrors = Record<string, string>;

const allowedName = /^[A-Za-z0-9!#$%^&*()\-_=+?]+$/;
const allowedPassword = /^[A-Za-z0-9!@#$%^&*()\-_=+?.]+$/;
export const passwordFormatError = "Use 12-72 characters from 3 of the 4 character groups";

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
    errors.password = passwordFormatError;
  } else {
    const groups = [/[A-Z]/, /[a-z]/, /\d/, /[!@#$%^&*()\-_=+?]/].filter((rule) =>
      rule.test(values.password),
    ).length;
    if (groups < 3) errors.password = passwordFormatError;
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

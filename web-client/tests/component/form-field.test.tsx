import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FormField } from "../../src/components/form-field";
import { PasswordRequirements } from "../../src/components/password-requirements";

describe("FormField", () => {
  it("connects validation feedback to its field", () => {
    render(<FormField id="display-name" label="Display name" error="Use at least two characters" />);

    expect(screen.getByLabelText("Display name")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("alert")).toHaveTextContent("Use at least two characters");
  });

  it("renders the exact password character groups in the hover tooltip", () => {
    render(<PasswordRequirements>At least 12 characters from 3 of the 4 character groups</PasswordRequirements>);

    const tooltip = screen.getByRole("tooltip");
    expect(tooltip).toHaveTextContent("Uppercase letters (A–Z)");
    expect(tooltip).toHaveTextContent("Lowercase letters (a–z)");
    expect(tooltip).toHaveTextContent("Digits (0–9)");
    expect(tooltip).toHaveTextContent("Special characters (!, #, $, %, ^, &, *, (, ), -, _, =, +,?,.)");
  });
});

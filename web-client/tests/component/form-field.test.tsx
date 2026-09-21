import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FormField } from "../../src/components/form-field";

describe("FormField", () => {
  it("connects validation feedback to its field", () => {
    render(<FormField id="display-name" label="Display name" error="Use at least two characters" />);

    expect(screen.getByLabelText("Display name")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("alert")).toHaveTextContent("Use at least two characters");
  });
});

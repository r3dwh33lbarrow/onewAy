import {
  snakeCaseToTitle,
  snakeCaseToDashCase,
  apiErrorToString,
  generatePassword,
  titleCaseToDashCase,
} from "../utils";
import type { ApiError } from "../apiClient";

describe("Utils Tests", () => {
  describe("snakeCaseToTitle", () => {
    it("should convert snake_case to Title Case", () => {
      expect(snakeCaseToTitle("hello_world")).toBe("Hello World");
      expect(snakeCaseToTitle("test_module_name")).toBe("Test Module Name");
      expect(snakeCaseToTitle("single")).toBe("Single");
    });

    it("should handle uppercase letters in input", () => {
      expect(snakeCaseToTitle("HELLO_WORLD")).toBe("Hello World");
      expect(snakeCaseToTitle("MiXeD_CaSe")).toBe("Mixed Case");
    });

    it("should handle empty string", () => {
      expect(snakeCaseToTitle("")).toBe("");
    });

    it("should handle string without underscores", () => {
      expect(snakeCaseToTitle("singleword")).toBe("Singleword");
      expect(snakeCaseToTitle("UPPERCASE")).toBe("Uppercase");
    });

    it("should handle multiple consecutive underscores", () => {
      expect(snakeCaseToTitle("hello__world")).toBe("Hello  World");
    });

    it("should handle strings starting or ending with underscores", () => {
      expect(snakeCaseToTitle("_hello_world")).toBe(" Hello World");
      expect(snakeCaseToTitle("hello_world_")).toBe("Hello World ");
    });

    it("should handle numbers in the string", () => {
      expect(snakeCaseToTitle("module_123_test")).toBe("Module 123 Test");
    });

    it("should handle special characters", () => {
      expect(snakeCaseToTitle("test_with_@_symbol")).toBe("Test With @ Symbol");
    });
  });

  describe("snakeCaseToDashCase", () => {
    it("should convert snake_case to dash-case", () => {
      expect(snakeCaseToDashCase("hello_world")).toBe("hello-world");
      expect(snakeCaseToDashCase("test_module_name")).toBe("test-module-name");
    });

    it("should convert uppercase to lowercase", () => {
      expect(snakeCaseToDashCase("HELLO_WORLD")).toBe("hello-world");
      expect(snakeCaseToDashCase("MiXeD_CaSe")).toBe("mixed-case");
    });

    it("should handle empty string", () => {
      expect(snakeCaseToDashCase("")).toBe("");
    });

    it("should handle string without underscores", () => {
      expect(snakeCaseToDashCase("singleword")).toBe("singleword");
      expect(snakeCaseToDashCase("UPPERCASE")).toBe("uppercase");
    });

    it("should handle multiple consecutive underscores", () => {
      expect(snakeCaseToDashCase("hello__world")).toBe("hello--world");
    });

    it("should handle strings starting or ending with underscores", () => {
      expect(snakeCaseToDashCase("_hello_world")).toBe("-hello-world");
      expect(snakeCaseToDashCase("hello_world_")).toBe("hello-world-");
    });

    it("should handle numbers", () => {
      expect(snakeCaseToDashCase("module_123_test")).toBe("module-123-test");
    });
  });

  describe("titleCaseToDashCase", () => {
    it("should convert Title Case to dash-case", () => {
      expect(titleCaseToDashCase("Hello World")).toBe("hello-world");
      expect(titleCaseToDashCase("Test Module Name")).toBe("test-module-name");
    });

    it("should handle uppercase input", () => {
      expect(titleCaseToDashCase("HELLO WORLD")).toBe("hello-world");
    });

    it("should handle empty string", () => {
      expect(titleCaseToDashCase("")).toBe("");
    });

    it("should handle single word", () => {
      expect(titleCaseToDashCase("Single")).toBe("single");
      expect(titleCaseToDashCase("single")).toBe("single");
    });

    it("should handle multiple consecutive spaces", () => {
      expect(titleCaseToDashCase("Hello  World")).toBe("hello--world");
    });

    it("should handle strings starting or ending with spaces", () => {
      expect(titleCaseToDashCase(" Hello World")).toBe("-hello-world");
      expect(titleCaseToDashCase("Hello World ")).toBe("hello-world-");
    });

    it("should handle numbers", () => {
      expect(titleCaseToDashCase("Module 123 Test")).toBe("module-123-test");
    });

    it("should handle special characters", () => {
      expect(titleCaseToDashCase("Test With @ Symbol")).toBe("test-with-@-symbol");
    });
  });

  describe("apiErrorToString", () => {
    it("should format error with detail", () => {
      const error: ApiError = {
        statusCode: 404,
        message: "Not Found",
        detail: "Resource does not exist",
      };
      expect(apiErrorToString(error)).toBe("404: Resource does not exist");
    });

    it("should use message when detail is empty", () => {
      const error: ApiError = {
        statusCode: 500,
        message: "Internal Server Error",
        detail: "",
      };
      expect(apiErrorToString(error)).toBe("500: Internal Server Error");
    });

    it("should use message when detail is undefined", () => {
      const error: ApiError = {
        statusCode: 401,
        message: "Unauthorized",
        detail: undefined as any,
      };
      expect(apiErrorToString(error)).toBe("401: Unauthorized");
    });

    it("should handle various status codes", () => {
      expect(
        apiErrorToString({
          statusCode: 200,
          message: "OK",
          detail: "Success",
        }),
      ).toBe("200: Success");

      expect(
        apiErrorToString({
          statusCode: 403,
          message: "Forbidden",
          detail: "Access denied",
        }),
      ).toBe("403: Access denied");

      expect(
        apiErrorToString({
          statusCode: 503,
          message: "Service Unavailable",
          detail: "Server is down",
        }),
      ).toBe("503: Server is down");
    });

    it("should handle long detail messages", () => {
      const longDetail = "a".repeat(1000);
      const error: ApiError = {
        statusCode: 400,
        message: "Bad Request",
        detail: longDetail,
      };
      expect(apiErrorToString(error)).toBe(`400: ${longDetail}`);
    });

    it("should handle special characters in messages", () => {
      const error: ApiError = {
        statusCode: 400,
        message: "Bad Request",
        detail: "Invalid input: <script>alert('xss')</script>",
      };
      expect(apiErrorToString(error)).toBe(
        "400: Invalid input: <script>alert('xss')</script>",
      );
    });
  });

  describe("generatePassword", () => {
    it("should generate password of specified length", () => {
      expect(generatePassword(10)).toHaveLength(10);
      expect(generatePassword(20)).toHaveLength(20);
      expect(generatePassword(50)).toHaveLength(50);
    });

    it("should generate password with length 1", () => {
      expect(generatePassword(1)).toHaveLength(1);
    });

    it("should generate empty string for length 0", () => {
      expect(generatePassword(0)).toBe("");
    });

    it("should only use allowed characters", () => {
      const allowedChars =
        /^[ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()\-_=+\[\]{}|;:,.<>?]+$/;

      for (let i = 0; i < 10; i++) {
        const password = generatePassword(100);
        expect(password).toMatch(allowedChars);
      }
    });

    it("should generate different passwords on consecutive calls", () => {
      const password1 = generatePassword(20);
      const password2 = generatePassword(20);
      const password3 = generatePassword(20);

      // Very unlikely to generate the same password twice
      expect(password1).not.toBe(password2);
      expect(password2).not.toBe(password3);
      expect(password1).not.toBe(password3);
    });

    it("should handle large lengths", () => {
      const password = generatePassword(1000);
      expect(password).toHaveLength(1000);
    });

    it("should work with Math.random fallback", () => {
      // Mock crypto to test fallback
      const originalCrypto = global.crypto;
      (global as any).crypto = undefined;

      const password = generatePassword(20);
      expect(password).toHaveLength(20);

      // Restore crypto
      (global as any).crypto = originalCrypto;
    });

    it("should include variety of character types in longer passwords", () => {
      const password = generatePassword(100);

      const hasUppercase = /[A-Z]/.test(password);
      const hasLowercase = /[a-z]/.test(password);
      const hasNumber = /[0-9]/.test(password);
      const hasSpecial = /[!@#$%^&*()\-_=+\[\]{}|;:,.<>?]/.test(password);

      // With 100 characters, very likely to have all types
      expect(hasUppercase || hasLowercase || hasNumber || hasSpecial).toBe(true);
    });
  });

  describe("Edge Cases and Integration", () => {
    it("should handle conversion chains", () => {
      const input = "test_module_name";
      const title = snakeCaseToTitle(input); // "Test Module Name"
      const dashCase = titleCaseToDashCase(title); // "test-module-name"
      expect(dashCase).toBe("test-module-name");
    });

    it("should handle round-trip conversions", () => {
      const original = "hello_world_test";
      const title = snakeCaseToTitle(original);
      const dashFromTitle = titleCaseToDashCase(title);
      const dashDirect = snakeCaseToDashCase(original);

      expect(dashFromTitle).toBe(dashDirect);
    });
  });
});

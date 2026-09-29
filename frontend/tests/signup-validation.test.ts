import { test } from "node:test";
import assert from "node:assert/strict";
import { validateSignup } from "../lib/signup-validation.ts";

const valid = { fullName: "Ajay Thomas", email: "ajay@example.com", password: "a long passphrase", confirmPassword: "a long passphrase" };

test("accepts valid values, trimmed names and email, and international names", () => {
  assert.deepEqual(validateSignup(valid), {});
  assert.deepEqual(validateSignup({ ...valid, fullName: "  李明  ", email: " ajay@example.com " }), {});
});
test("requires all fields", () => {
  assert.deepEqual(Object.keys(validateSignup({ fullName: " ", email: "", password: "", confirmPassword: "" })), ["fullName", "email", "password", "confirmPassword"]);
});
test("rejects invalid and oversized email addresses", () => {
  for (const email of ["no-at-sign", "a@", "a@b", "a b@example.com", "a@@example.com", "a".repeat(250) + "@example.com"]) {
    assert.ok(validateSignup({ ...valid, email }).email);
  }
});
test("requires 8 to 128 password characters and matching confirmation", () => {
  for (const password of ["1234567", " ".repeat(8), "x".repeat(129)]) {
    assert.ok(validateSignup({ ...valid, password, confirmPassword: password }).password);
  }
  assert.ok(validateSignup({ ...valid, confirmPassword: "different" }).confirmPassword);
  assert.ok(validateSignup({ ...valid, confirmPassword: "" }).confirmPassword);
  assert.deepEqual(validateSignup({ ...valid, password: "12345678", confirmPassword: "12345678" }), {});
});
test("does not trim passwords when comparing them", () => {
  assert.ok(validateSignup({ ...valid, password: " password ", confirmPassword: "password" }).confirmPassword);
});

"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { CheckCircle2, Eye, EyeOff, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { createClient } from "@/lib/supabase/client";
import { validateSignup, type SignupValues, type SignupErrors } from "@/lib/signup-validation";

const fields: { name: keyof SignupValues; label: string; placeholder: string; autocomplete: string }[] = [
  { name: "fullName", label: "Full name", placeholder: "Your name", autocomplete: "name" },
  { name: "email", label: "Email", placeholder: "you@example.com", autocomplete: "email" },
  { name: "password", label: "Password", placeholder: "At least 8 characters", autocomplete: "new-password" },
  { name: "confirmPassword", label: "Confirm password", placeholder: "Enter your password again", autocomplete: "new-password" },
];

export function SignupForm({ ...props }: React.ComponentProps<typeof Card>) {
  const [values, setValues] = useState<SignupValues>({ fullName: "", email: "", password: "", confirmPassword: "" });
  const [errors, setErrors] = useState<SignupErrors>({});
  const [errorMessage, setErrorMessage] = useState("");
  const [loading, setLoading] = useState<"email" | "google" | null>(null);
  const [success, setSuccess] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);
  const pending = useRef(false);
  const router = useRouter();

  const redirectUrl = () => `${process.env.NEXT_PUBLIC_SITE_URL || window.location.origin}/auth/callback?next=/dashboard`;

  async function handleGoogleSignup() {
    if (pending.current) return;
    pending.current = true;
    setLoading("google");
    setErrorMessage("");
    try {
      const { error } = await createClient().auth.signInWithOAuth({ provider: "google", options: { redirectTo: redirectUrl() } });
      if (error) throw error;
    } catch {
      setErrorMessage("Could not connect to Google. Please try again.");
      setLoading(null);
      pending.current = false;
    }
  }

  async function handleSignup(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending.current || success) return;
    const nextErrors = validateSignup(values);
    setErrors(nextErrors);
    setErrorMessage("");
    const firstError = Object.keys(nextErrors)[0];
    if (firstError) {
      formRef.current?.querySelector<HTMLInputElement>(`[name="${firstError}"]`)?.focus();
      return;
    }
    pending.current = true;
    setLoading("email");
    try {
      const { data, error } = await createClient().auth.signUp({
        email: values.email.trim(),
        password: values.password,
        options: { data: { full_name: values.fullName.trim() }, emailRedirectTo: redirectUrl() },
      });
      if (error) {
        setErrorMessage(error.message);
        return;
      }
      if (data.session) {
        router.push("/dashboard");
        router.refresh();
      } else {
        setSuccess(true);
        setValues((previous) => ({ ...previous, password: "", confirmPassword: "" }));
      }
    } catch {
      setErrorMessage("We couldn’t create your account. Check your connection and try again.");
    } finally {
      pending.current = false;
      setLoading(null);
    }
  }

  return (
    <Card {...props}>
      <CardHeader>
        <CardTitle>{success ? "Check your inbox" : "Create an account"}</CardTitle>
        <CardDescription>{success ? "One more step before your first dataset." : "A little less spreadsheet work starts here."}</CardDescription>
      </CardHeader>
      <CardContent>
        {success ? (
          <div role="status" className="space-y-5 text-sm">
            <CheckCircle2 className="size-8 text-primary" aria-hidden="true" />
            <p>If your address is eligible, a confirmation link has been sent to <strong>{values.email.trim()}</strong>. Check your inbox and spam folder.</p>
            <Button asChild className="w-full"><Link href="/auth/login">Back to sign in</Link></Button>
          </div>
        ) : (
          <form ref={formRef} onSubmit={handleSignup} noValidate aria-busy={loading !== null}>
            <FieldGroup>
              {fields.map(({ name, label, placeholder, autocomplete }) => {
                const isPassword = name === "password" || name === "confirmPassword";
                return (
                  <Field key={name} data-invalid={!!errors[name]}>
                    <FieldLabel htmlFor={name}>{label}</FieldLabel>
                    <div className="relative">
                      <Input
                        id={name} name={name} value={values[name]} placeholder={placeholder}
                        type={isPassword ? (showPassword ? "text" : "password") : name === "email" ? "email" : "text"}
                        autoComplete={autocomplete} required disabled={loading !== null}
                        maxLength={isPassword ? 128 : name === "email" ? 254 : 100}
                        aria-invalid={!!errors[name]}
                        aria-describedby={errors[name] ? `${name}-error` : name === "password" ? "password-help" : undefined}
                        className={name === "password" ? "pr-10" : undefined}
                        onBlur={() => setErrors((previous) => ({ ...previous, [name]: validateSignup(values)[name] }))}
                        onChange={(event) => {
                          const next = { ...values, [name]: event.target.value };
                          setValues(next);
                          setErrors((previous) => {
                            const checked = validateSignup(next);
                            return { ...previous, [name]: previous[name] ? checked[name] : undefined,
                              ...(name === "password" && previous.confirmPassword ? { confirmPassword: checked.confirmPassword } : {}) };
                          });
                          setErrorMessage("");
                        }}
                      />
                      {name === "password" && (
                        <button type="button" className="absolute inset-y-0 right-0 flex w-10 items-center justify-center rounded-md text-muted-foreground focus-visible:outline-2 focus-visible:outline-ring"
                          onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? "Hide passwords" : "Show passwords"} aria-pressed={showPassword}>
                          {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                        </button>
                      )}
                    </div>
                    {errors[name] ? <p id={`${name}-error`} role="alert" className="text-xs text-destructive">{errors[name]}</p>
                      : name === "password" ? <FieldDescription id="password-help">Use 8–128 characters. A longer passphrase works well.</FieldDescription> : null}
                  </Field>
                );
              })}
              <Field>
                {errorMessage && <p role="alert" className="text-sm text-destructive">{errorMessage}</p>}
                <Button type="submit" disabled={loading !== null}>{loading === "email" && <Loader2 className="size-4 animate-spin" />} {loading === "email" ? "Creating account…" : "Create account"}</Button>
                <Button variant="outline" type="button" onClick={handleGoogleSignup} disabled={loading !== null}>{loading === "google" && <Loader2 className="size-4 animate-spin" />}Continue with Google</Button>
                <FieldDescription className="text-center">Already have an account? <Link href="/auth/login">Sign in</Link></FieldDescription>
              </Field>
            </FieldGroup>
          </form>
        )}
      </CardContent>
    </Card>
  );
}

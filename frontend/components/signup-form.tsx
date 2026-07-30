"use client";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { createClient } from "@/lib/supabase/client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
export function SignupForm({ ...props }: React.ComponentProps<typeof Card>) {
  const [fullName, setFullName] = useState<string>("");
  const [email, SetEmail] = useState<string>("");
  const [password, SetPassword] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const supabase = createClient();
  const router = useRouter();
  const handleGoogleSignup = async (): Promise<void> => {
    setErrorMessage("");
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${process.env.NEXT_PUBLIC_SITE_URL || window.location.origin}/auth/callback?next=/dashboard`,
      },
    });

    if (error) setErrorMessage(error.message);
  };
  const handleSignup = async (
    e: React.FormEvent<HTMLFormElement>,
  ): Promise<void> => {
    e.preventDefault();
    setErrorMessage("");

    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          full_name: fullName,
        },
        emailRedirectTo: `${process.env.NEXT_PUBLIC_SITE_URL || window.location.origin}/auth/callback?next=/dashboard`,
      },
    });

    if (error) {
      if (error.message.toLowerCase().includes("already")) {
        setErrorMessage("User already registered. Please sign in.");
      } else {
        setErrorMessage(error.message);
      }
      return;
    }

    if (data.session) {
      router.push("/dashboard");
    } else {
      alert(
        "Account created successfully! Please check your email to verify your account.",
      );
    }
  };
  return (
    <Card {...props}>
      <CardHeader>
        <CardTitle>Create an account</CardTitle>
        <CardDescription>
          Enter your information below to create your account
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSignup}>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="name">Full Name</FieldLabel>
              <Input
                id="name"
                type="text"
                placeholder="John Doe"
                required
                onChange={(e) => setFullName(e.target.value)}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="email">Email</FieldLabel>
              <Input
                id="email"
                type="email"
                placeholder="m@example.com"
                required
                onChange={(e) => {
                  SetEmail(e.target.value);
                }}
              />
              <FieldDescription>
                We&apos;ll use this to contact you. We will not share your email
                with anyone else.
              </FieldDescription>
            </Field>
            <Field>
              <FieldLabel htmlFor="password">Password</FieldLabel>
              <Input
                id="password"
                type="password"
                onChange={(e) => {
                  SetPassword(e.target.value);
                }}
                required
              />
              <FieldDescription>
                Must be at least 8 characters long.
              </FieldDescription>
            </Field>
            <Field>
              <FieldLabel htmlFor="confirm-password">
                Confirm Password
              </FieldLabel>
              <Input id="confirm-password" type="password" required />
              <FieldDescription>Please confirm your password.</FieldDescription>
            </Field>
            <FieldGroup>
              <Field>
                {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}
                <Button type="submit">Create Account</Button>
                <Button variant="outline" type="button" onClick={handleGoogleSignup}>
                  Sign up with Google
                </Button>
                <FieldDescription className="px-6 text-center">
                  Already have an account?{" "}
                  <Link href="/auth/login">Sign in</Link>
                </FieldDescription>
              </Field>
            </FieldGroup>
          </FieldGroup>
        </form>
      </CardContent>
    </Card>
  );
}

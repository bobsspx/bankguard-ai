"use client";

import {
  FormEvent,
  useState,
} from "react";
import { useRouter } from "next/navigation";


export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] =
    useState(
      "fraud@bankguard.demo",
    );

  const [
    password,
    setPassword,
  ] = useState("");

  const [
    error,
    setError,
  ] = useState("");

  const [
    loading,
    setLoading,
  ] = useState(false);


  async function handleSubmit(
    event: FormEvent,
  ) {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {
      const response =
        await fetch(
          "/api/auth/login",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              email,
              password,
            }),
          },
        );

      const data =
        await response.json();

      if (!response.ok) {
        setError(
          data.error ??
            "Login failed.",
        );

        return;
      }

      router.push("/");
      router.refresh();

    } catch {
      setError(
        "Unable to contact the server.",
      );

    } finally {
      setLoading(false);
    }
  }


  return (
    <main className="loginPage">
      <section className="loginBrand">
        <div>
          <div className="brandMark">
            BG
          </div>

          <p className="eyebrow">
            BANKING SECURITY PLATFORM
          </p>

          <h1>
            BankGuard
            <span> AI</span>
          </h1>

          <p className="loginIntro">
            Fraud detection,
            transaction monitoring
            and security operations.
          </p>
        </div>

        <div className="loginSecurity">
          <span>
            SECURE ACCESS
          </span>

          <p>
            Protected by JWT
            authentication and
            role-based access control.
          </p>
        </div>
      </section>

      <section className="loginPanel">
        <form
          className="loginForm"
          onSubmit={handleSubmit}
        >
          <div>
            <p className="eyebrow">
              ANALYST CONSOLE
            </p>

            <h2>Sign in</h2>

            <p className="muted">
              Authorized personnel only.
            </p>
          </div>

          <label>
            Email

            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) =>
                setEmail(
                  event.target.value,
                )
              }
              required
            />
          </label>

          <label>
            Password

            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) =>
                setPassword(
                  event.target.value,
                )
              }
              required
            />
          </label>

          {error && (
            <div className="errorBox">
              {error}
            </div>
          )}

          <button
            className="primaryButton"
            disabled={loading}
            type="submit"
          >
            {loading
              ? "Signing in..."
              : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
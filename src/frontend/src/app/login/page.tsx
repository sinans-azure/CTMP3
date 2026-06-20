"use client"

import * as React from "react"
import { Suspense } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { useMsal } from "@azure/msal-react"
import { loginRequest, API_BASE_URL } from "@/lib/msal-config"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Terminal, Shield, ArrowRight, ShieldCheck, Cpu, AlertCircle } from "lucide-react"

function LoginContent() {
  const { instance } = useMsal()
  const router = useRouter()
  const searchParams = useSearchParams()
  const [username, setUsername] = React.useState("")
  const [password, setPassword] = React.useState("")
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState("")
  const [tokenLoading, setTokenLoading] = React.useState(false)

  // Handle invitation token (auto-login link)
  React.useEffect(() => {
    const inviteToken = searchParams.get("token")
    if (inviteToken) {
      setTokenLoading(true)
      const verifyToken = async () => {
        try {
          const res = await fetch(`${API_BASE_URL}/api/auth/invite?token=${inviteToken}`)
          if (!res.ok) {
            throw new Error("Invalid token")
          }
          const data = await res.json()
          if (data && data.token && data.user) {
            localStorage.setItem("ctmp_token", data.token)
            localStorage.setItem("ctmp_user", JSON.stringify(data.user))
            router.push("/dashboard")
          } else {
            throw new Error("Invalid data format")
          }
        } catch (e) {
          console.error(e)
          setError("Invalid or expired invitation token. Please log in manually.")
          setTokenLoading(false)
        }
      }
      verifyToken()
    }
  }, [searchParams, router])

  const handleCredentialsLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError("")
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      })
      if (!res.ok) {
        throw new Error("Invalid username or password")
      }
      const data = await res.json()
      if (data && data.token && data.user) {
        localStorage.setItem("ctmp_token", data.token)
        localStorage.setItem("ctmp_user", JSON.stringify(data.user))
        router.push("/dashboard")
      }
    } catch (e: any) {
      setError(e.message || "Login failed. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  const handleSsoLogin = async () => {
    setLoading(true)
    setError("")
    try {
      await instance.loginRedirect(loginRequest)
    } catch (e) {
      console.error("SSO Login redirect failed", e)
      setError("SSO Login failed. Please try local credentials.")
      setLoading(false)
    }
  }

  if (tokenLoading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 text-zinc-50">
        <div className="flex flex-col items-center gap-4">
          <span className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
          <p className="text-sm text-zinc-400">Verifying invitation token...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-zinc-950 px-4 py-12">
      {/* Decorative gradient glow background */}
      <div className="absolute top-1/4 left-1/2 -z-10 h-[500px] w-[500px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-indigo-500/10 blur-[80px]" />

      <div className="w-full max-w-md space-y-6">
        <div className="flex flex-col items-center text-center space-y-2">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 shadow-lg shadow-indigo-600/30 text-white font-bold mb-2">
            <Terminal className="h-6 w-6" />
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-zinc-50">
            Sign In to CTMP
          </h1>
          <p className="text-sm text-zinc-400">
            Trainer and Student portal entrance.
          </p>
        </div>

        <Card className="border-zinc-800 bg-zinc-950/60 shadow-2xl">
          <CardHeader className="space-y-1">
            <CardTitle className="text-xl font-bold">Portal Access</CardTitle>
            <CardDescription className="text-xs text-zinc-400">
              Sign in with local credentials or corporate Single Sign-On.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCredentialsLogin} className="space-y-4">
              {error && (
                <div className="flex items-center gap-2 p-3 text-xs rounded-lg border border-red-500/30 bg-red-500/10 text-red-400">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}
              <div className="space-y-1.5">
                <Label htmlFor="username" className="text-zinc-400 text-xs">Username / UPN</Label>
                <Input
                  id="username"
                  type="text"
                  placeholder="e.g. trainer1 or student1"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  className="bg-zinc-900 border-zinc-800 text-zinc-50"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="password" className="text-zinc-400 text-xs">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="bg-zinc-900 border-zinc-800 text-zinc-50"
                />
              </div>

              <Button
                type="submit"
                disabled={loading}
                className="w-full bg-zinc-50 hover:bg-zinc-200 text-zinc-950 font-bold h-10 shadow-lg shadow-zinc-500/10 mt-2"
              >
                {loading ? (
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-950 border-t-transparent" />
                ) : (
                  "Log In with Credentials"
                )}
              </Button>
            </form>

            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-zinc-900" />
              </div>
              <div className="relative flex justify-center text-[10px] uppercase">
                <span className="bg-zinc-950 px-2 text-zinc-500">Or continue with</span>
              </div>
            </div>

            <Button
              onClick={handleSsoLogin}
              disabled={loading}
              className="w-full bg-indigo-600 text-white font-semibold hover:bg-indigo-500 h-10 shadow-lg shadow-indigo-600/20 active:scale-[0.98] transition-transform duration-100 flex items-center justify-center gap-2"
            >
              Sign In with SSO
              <ArrowRight className="h-4 w-4" />
            </Button>
          </CardContent>
          <CardFooter className="justify-center border-t border-zinc-900 py-3.5">
            <div className="flex items-center gap-1.5 text-xs text-zinc-500">
              <Shield className="h-3.5 w-3.5" />
              SSO logs are secure & audited
            </div>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 text-zinc-50">
        <span className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
      </div>
    }>
      <LoginContent />
    </Suspense>
  )
}


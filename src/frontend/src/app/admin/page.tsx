"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { API_BASE_URL } from "@/lib/msal-config"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Terminal, Shield, ArrowRight, ShieldCheck, AlertCircle } from "lucide-react"

export default function AdminLoginPage() {
  const router = useRouter()
  const [username, setUsername] = React.useState("")
  const [password, setPassword] = React.useState("")
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState("")

  const handleAdminLogin = async (e: React.FormEvent) => {
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
        const roles = data.user.roles || []
        if (!roles.includes("Admin")) {
          throw new Error("Access Denied. Admin role required.")
        }
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

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-zinc-950 px-4 py-12">
      {/* Decorative red/crimson gradient glow background specifically for administrative security feel */}
      <div className="absolute top-1/4 left-1/2 -z-10 h-[500px] w-[500px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-red-600/5 blur-[80px]" />
      <div className="absolute top-1/2 left-1/3 -z-10 h-[300px] w-[300px] rounded-full bg-indigo-600/5 blur-[60px]" />

      <div className="w-full max-w-md space-y-6">
        <div className="flex flex-col items-center text-center space-y-2">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-red-950/40 border border-red-500/20 shadow-lg text-red-500 font-bold mb-2">
            <Shield className="h-6 w-6" />
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-zinc-50">
            Admin Console
          </h1>
          <p className="text-sm text-zinc-400">
            Authorized administrators only.
          </p>
        </div>

        <Card className="border-zinc-800 bg-zinc-950/60 shadow-2xl">
          <CardHeader className="space-y-1">
            <CardTitle className="text-xl font-bold">Admin Entry</CardTitle>
            <CardDescription className="text-xs text-zinc-400">
              Provide your administrator credentials to login.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAdminLogin} className="space-y-4">
              {error && (
                <div className="flex items-center gap-2 p-3 text-xs rounded-lg border border-red-500/30 bg-red-500/10 text-red-400">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}
              <div className="space-y-1.5">
                <Label htmlFor="username" className="text-zinc-400 text-xs">Admin Username</Label>
                <Input
                  id="username"
                  type="text"
                  placeholder="e.g. admin1"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  className="bg-zinc-900 border-zinc-800 text-zinc-50 font-mono"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="password" className="text-zinc-400 text-xs">Admin Password</Label>
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
                className="w-full bg-red-600 hover:bg-red-500 text-white font-bold h-10 shadow-lg shadow-red-600/25 mt-2"
              >
                {loading ? (
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                ) : (
                  "Access Control Center"
                )}
              </Button>
            </form>
          </CardContent>
          <CardFooter className="justify-center border-t border-zinc-900 py-3.5">
            <div className="flex items-center gap-1.5 text-xs text-zinc-500">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
              Secure HSM authentication enabled
            </div>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}

"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { useMsal } from "@azure/msal-react"
import { useAuth } from "@/hooks/use-auth"
import { loginRequest } from "@/lib/msal-config"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Terminal, Shield, ArrowRight, ShieldCheck, Cpu } from "lucide-react"

export default function LandingPage() {
  const { instance } = useMsal()
  const { isAuthenticated, name } = useAuth()
  const router = useRouter()
  const [loading, setLoading] = React.useState(false)

  React.useEffect(() => {
    if (isAuthenticated) {
      router.push("/dashboard")
    }
  }, [isAuthenticated, router])

  const handleLogin = async () => {
    setLoading(true)
    try {
      await instance.loginRedirect(loginRequest)
    } catch (e) {
      console.error("Login redirect failed", e)
      setLoading(false)
    }
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-zinc-950 px-4 py-12">
      {/* Decorative gradient glow background */}
      <div className="absolute top-1/4 left-1/2 -z-10 h-[500px] w-[500px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-indigo-500/10 blur-[80px]" />
      <div className="absolute top-1/2 left-1/3 -z-10 h-[300px] w-[300px] rounded-full bg-blue-500/10 blur-[60px]" />

      <div className="w-full max-w-md space-y-6 animate-in fade-in duration-700">
        <div className="flex flex-col items-center text-center space-y-2">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 shadow-lg shadow-indigo-600/30 text-white font-bold mb-2">
            <Terminal className="h-6 w-6" />
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-zinc-50 sm:text-4xl">
            Contoso CTMP
          </h1>
          <p className="text-sm text-zinc-400 max-w-xs">
            Cloud Training Management Portal. Orchestrate sandbox lab environments at scale.
          </p>
        </div>

        <Card className="glass-card glass-card-hover border-zinc-800 bg-zinc-950/60 shadow-2xl transition-all duration-300">
          <CardHeader className="text-center space-y-1">
            <CardTitle className="text-xl font-bold text-zinc-50">Portal Entry</CardTitle>
            <CardDescription className="text-xs text-zinc-400">
              Sign in with your organization Microsoft Entra ID.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-3 text-center py-2">
              <div className="p-3 rounded-lg bg-zinc-900/50 border border-zinc-800/80 flex flex-col items-center">
                <Cpu className="h-5 w-5 text-indigo-400 mb-1" />
                <span className="text-[10px] text-zinc-400">Sandbox</span>
              </div>
              <div className="p-3 rounded-lg bg-zinc-900/50 border border-zinc-800/80 flex flex-col items-center">
                <ShieldCheck className="h-5 w-5 text-emerald-400 mb-1" />
                <span className="text-[10px] text-zinc-400">Secure</span>
              </div>
              <div className="p-3 rounded-lg bg-zinc-900/50 border border-zinc-800/80 flex flex-col items-center">
                <Terminal className="h-5 w-5 text-amber-400 mb-1" />
                <span className="text-[10px] text-zinc-400">AWS OIDC</span>
              </div>
            </div>

            <Button
              onClick={handleLogin}
              disabled={loading || isAuthenticated}
              className="w-full bg-indigo-600 text-white font-semibold hover:bg-indigo-500 h-10 shadow-lg shadow-indigo-600/20 active:scale-[0.98] transition-transform duration-100 flex items-center justify-center gap-2"
            >
              {loading ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                <>
                  Sign In with SSO
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </Button>
          </CardContent>
          <CardFooter className="justify-center border-t border-zinc-900 py-3.5">
            <div className="flex items-center gap-1.5 text-xs text-zinc-500">
              <Shield className="h-3.5 w-3.5" />
              Compliance and auditing enforced
            </div>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}

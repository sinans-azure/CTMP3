"use client"

import * as React from "react"
import { useMsal } from "@azure/msal-react"
import { apiScopes, API_BASE_URL } from "@/lib/msal-config"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Activity, Radio, AlertCircle, CheckCircle2 } from "lucide-react"

interface FeedActivity {
  id: string
  user: string
  action: string
  resource: string
  timestamp: string
  status: "success" | "warning" | "error" | "info"
}

export function ActivityFeed() {
  const { instance, accounts } = useMsal()
  const [activities, setActivities] = React.useState<FeedActivity[]>([
    {
      id: "1",
      user: "john.doe@contoso.com",
      action: "Created EC2 Instance",
      resource: "i-09d2983f82a173",
      timestamp: new Date(Date.now() - 5000 * 60).toISOString(),
      status: "success",
    },
    {
      id: "2",
      user: "trainer.jane@contoso.com",
      action: "Configured OIDC Role",
      resource: "arn:aws:iam::123456789012:role/CTMP-OIDC-Role",
      timestamp: new Date(Date.now() - 12000 * 60).toISOString(),
      status: "success",
    },
    {
      id: "3",
      user: "billing.system@contoso.com",
      action: "Budget Limit Warning (80%)",
      resource: "Budget: CTMP-June",
      timestamp: new Date(Date.now() - 45000 * 60).toISOString(),
      status: "warning",
    },
  ])
  const [isConnected, setIsConnected] = React.useState(false)

  React.useEffect(() => {
    let eventSource: EventSource | null = null

    const initSSE = async () => {
      if (accounts.length === 0) return

      try {
        const tokenResponse = await instance.acquireTokenSilent({
          ...apiScopes,
          account: accounts[0],
        })
        const token = tokenResponse.accessToken

        // Establish SSE connection passing token in query
        const url = `${API_BASE_URL}/api/audit/stream?token=${encodeURIComponent(token)}`
        eventSource = new EventSource(url)

        eventSource.onopen = () => {
          setIsConnected(true)
        }

        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            const newAct: FeedActivity = {
              id: data.id || Math.random().toString(),
              user: data.user || "system",
              action: data.action || "Activity",
              resource: data.resource || "",
              timestamp: data.timestamp || new Date().toISOString(),
              status: data.status || "info",
            }
            setActivities((prev) => [newAct, ...prev.slice(0, 19)])
          } catch (err) {
            console.error("Failed to parse event data", err)
          }
        }

        eventSource.onerror = () => {
          setIsConnected(false)
          eventSource?.close()
        }
      } catch (err) {
        console.error("Error setting up EventSource", err)
      }
    }

    initSSE()

    // Add a simulated log generator if not connected, to showcase visual premium fidelity
    const interval = setInterval(() => {
      if (!isConnected) {
        const mockUsers = ["admin@contoso.com", "trainer.bob@contoso.com", "student.alice@contoso.com"]
        const mockActions = ["Started Instance", "Stopped Instance", "Joined Training Group", "Generated AWS Template"]
        const mockResources = ["i-0a8b9c10d", "i-09d2983f82a173", "Group: AWS-101", "cfn-oidc.json"]
        const mockStatuses: Array<"success" | "warning" | "info"> = ["success", "info", "warning"]

        const randomUser = mockUsers[Math.floor(Math.random() * mockUsers.length)]
        const randomAction = mockActions[Math.floor(Math.random() * mockActions.length)]
        const randomResource = mockResources[Math.floor(Math.random() * mockResources.length)]
        const randomStatus = mockStatuses[Math.floor(Math.random() * mockStatuses.length)]

        const newAct: FeedActivity = {
          id: Math.random().toString(),
          user: randomUser,
          action: randomAction,
          resource: randomResource,
          timestamp: new Date().toISOString(),
          status: randomStatus,
        }

        setActivities((prev) => [newAct, ...prev.slice(0, 8)])
      }
    }, 15000)

    return () => {
      if (eventSource) {
        eventSource.close()
      }
      clearInterval(interval)
    }
  }, [accounts, instance, isConnected])

  return (
    <Card className="bg-zinc-950/40 backdrop-blur-md border border-zinc-800/80">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <CardTitle className="text-base font-semibold text-zinc-50">Live Audit Stream</CardTitle>
          <CardDescription className="text-xs text-zinc-400">
            Real-time infrastructure and portal operations feed.
          </CardDescription>
        </div>
        <div className="flex items-center gap-1.5 rounded-full bg-zinc-900 border border-zinc-800 px-2.5 py-1 text-xs text-zinc-400">
          <span className={`h-1.5 w-1.5 rounded-full ${isConnected ? "bg-emerald-500 animate-pulse" : "bg-zinc-600"}`} />
          {isConnected ? "Connected" : "Simulated"}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4 max-h-[350px] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-zinc-800">
          {activities.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 text-center text-zinc-500 text-xs">
              <Activity className="h-8 w-8 mb-2 stroke-1" />
              Waiting for events...
            </div>
          ) : (
            activities.map((activity) => (
              <div key={activity.id} className="flex gap-3 text-xs border-b border-zinc-900 pb-3 last:border-0 last:pb-0">
                <div className="mt-0.5">
                  {activity.status === "warning" ? (
                    <AlertCircle className="h-4 w-4 text-yellow-500" />
                  ) : activity.status === "error" ? (
                    <AlertCircle className="h-4 w-4 text-red-500" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4 text-indigo-400" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between gap-2">
                    <span className="font-semibold text-zinc-300 truncate">{activity.user}</span>
                    <span className="text-[10px] text-zinc-500 whitespace-nowrap">
                      {new Date(activity.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                  </div>
                  <p className="text-zinc-400 font-medium">{activity.action}</p>
                  {activity.resource && (
                    <code className="inline-block mt-1 bg-zinc-900 border border-zinc-800 text-[10px] px-1 rounded font-mono text-indigo-300 max-w-full truncate">
                      {activity.resource}
                    </code>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  )
}

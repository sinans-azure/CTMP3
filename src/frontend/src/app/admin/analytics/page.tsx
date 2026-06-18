"use client"

import * as React from "react"
import { InstanceChart } from "@/components/dashboard/instance-chart"
import { CostChart } from "@/components/dashboard/cost-chart"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { BarChart3, TrendingUp, TrendingDown, Users, Award, Percent } from "lucide-react"

export default function AdminAnalyticsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-zinc-50">Analytics Console</h1>
        <p className="text-sm text-zinc-400">
          Deeper insights into instance lifespans, resource utilization, and cost optimization.
        </p>
      </div>

      {/* Highlights Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card className="bg-zinc-950/40 border-zinc-800">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold text-zinc-400 uppercase">Average Instance Lifespan</CardTitle>
            <Award className="h-4 w-4 text-indigo-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-zinc-50">3.8 Hours</div>
            <p className="text-[11px] text-zinc-400 mt-1 flex items-center gap-1">
              <TrendingDown className="h-3 w-3 text-emerald-400" />
              Decreased by 12% due to auto-shutdown policies
            </p>
          </CardContent>
        </Card>

        <Card className="bg-zinc-950/40 border-zinc-800">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold text-zinc-400 uppercase">Peak Running Load</CardTitle>
            <Users className="h-4 w-4 text-emerald-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-zinc-50">42 Instances</div>
            <p className="text-[11px] text-zinc-400 mt-1 flex items-center gap-1">
              <TrendingUp className="h-3 w-3 text-indigo-400" />
              Observed on Wednesdays (OIDC workshop days)
            </p>
          </CardContent>
        </Card>

        <Card className="bg-zinc-950/40 border-zinc-800">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold text-zinc-400 uppercase">OIDC Setup Success Rate</CardTitle>
            <Percent className="h-4 w-4 text-amber-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-zinc-50">94.2%</div>
            <p className="text-[11px] text-zinc-400 mt-1 flex items-center gap-1">
              Based on CloudFormation template stack completions
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <InstanceChart />
        <CostChart />
      </div>
    </div>
  )
}

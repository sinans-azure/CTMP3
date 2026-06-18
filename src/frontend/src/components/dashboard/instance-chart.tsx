"use client"

import * as React from "react"
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltipContent } from "@/components/ui/chart"

const chartData = [
  { day: "Mon", active: 4, stopped: 2 },
  { day: "Tue", active: 8, stopped: 3 },
  { day: "Wed", active: 15, stopped: 5 },
  { day: "Thu", active: 12, stopped: 6 },
  { day: "Fri", active: 18, stopped: 4 },
  { day: "Sat", active: 9, stopped: 8 },
  { day: "Sun", active: 14, stopped: 5 },
]

const chartConfig = {
  active: {
    label: "Running",
    color: "#818cf8", // indigo-400
  },
  stopped: {
    label: "Stopped",
    color: "#f87171", // red-400
  },
}

export function InstanceChart() {
  return (
    <Card className="bg-zinc-950/40 backdrop-blur-md border border-zinc-800/80">
      <CardHeader className="flex flex-col gap-1 pb-4">
        <CardTitle className="text-base font-semibold text-zinc-50">EC2 Lifecycle Trends</CardTitle>
        <CardDescription className="text-xs text-zinc-400">
          Daily running and stopped cloud training instances.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[280px] w-full">
          <ChartContainer config={chartConfig} className="h-full w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={chartData}
                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="activeGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#818cf8" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#818cf8" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="stoppedGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f87171" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#f87171" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                <XAxis
                  dataKey="day"
                  stroke="#71717a"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke="#71717a"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  allowDecimals={false}
                />
                <Tooltip content={<ChartTooltipContent />} />
                <Area
                  type="monotone"
                  dataKey="active"
                  stroke="#818cf8"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#activeGrad)"
                />
                <Area
                  type="monotone"
                  dataKey="stopped"
                  stroke="#f87171"
                  strokeWidth={1.5}
                  fillOpacity={1}
                  fill="url(#stoppedGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </ChartContainer>
        </div>
      </CardContent>
    </Card>
  )
}

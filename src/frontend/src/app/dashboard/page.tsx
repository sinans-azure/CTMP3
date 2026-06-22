"use client";

import * as React from "react";
import { useAuth } from "@/hooks/use-auth";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { InstanceChart } from "@/components/dashboard/instance-chart";
import { CostChart } from "@/components/dashboard/cost-chart";
import { ActivityFeed } from "@/components/dashboard/activity-feed";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Sparkles, Terminal } from "lucide-react";

export default function DashboardPage() {
  const { name, isAdmin, isTrainer, isStudent } = useAuth();

  const roleLabel = React.useMemo(() => {
    if (isAdmin) return "System Administrator";
    if (isTrainer) return "Training Instructor";
    return "Student Member";
  }, [isAdmin, isTrainer]);

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-zinc-50">
            Welcome back, {name || "User"}
          </h1>
          <p className="text-sm text-zinc-400">
            Signed in as{" "}
            <span className="font-semibold text-indigo-400">{roleLabel}</span>.
            Access all resources below.
          </p>
        </div>
      </div>

      {/* Stats Cards Section */}
      <StatsCards />

      {/* Main Charts / Feed Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* Instance Trends (Left side span 2 on lg screens) */}
        <div className="lg:col-span-2 space-y-6">
          <InstanceChart />
          {(isAdmin || isTrainer) && <CostChart />}
        </div>

        {/* Real-time Activity Feed (Right side) */}
        <div>
          <ActivityFeed />
        </div>
      </div>
    </div>
  );
}

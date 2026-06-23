"use client";

import * as React from "react";
import { useAuth } from "@/hooks/use-auth";
import { useApiClient } from "@/hooks/use-api-client";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { InstanceChart } from "@/components/dashboard/instance-chart";
import { CostChart } from "@/components/dashboard/cost-chart";
import { ActivityFeed } from "@/components/dashboard/activity-feed";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

interface AnalyticsDashboardResponse {
  active_instances: number;
  total_users: number;
  cpu_utilization_avg: number;
  active_groups: number;
  total_spend_usd: number;
}

interface BillingSummaryResponse {
  total_platform_cost: number;
  active_groups_count: number;
  active_students_count: number;
  top_spending_group_id: string;
  currency: string;
  monthly_budget: number;
  budget_utilization_percentage: number;
}

interface InstanceMetricsPoint {
  timestamp: string;
  running_count: number;
  stopped_count: number;
}

interface CostMetricsPoint {
  timestamp: string;
  cumulative_cost_usd: number;
}

export default function DashboardPage() {
  const { name, isAdmin, isTrainer } = useAuth();
  const api = useApiClient();

  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");

  const [analyticsData, setAnalyticsData] = React.useState<AnalyticsDashboardResponse | null>(null);
  const [billingData, setBillingData] = React.useState<BillingSummaryResponse | null>(null);
  const [instanceMetrics, setInstanceMetrics] = React.useState<InstanceMetricsPoint[]>([]);
  const [costMetrics, setCostMetrics] = React.useState<CostMetricsPoint[]>([]);

  const roleLabel = React.useMemo(() => {
    if (isAdmin) return "System Administrator";
    if (isTrainer) return "Training Instructor";
    return "Student Member";
  }, [isAdmin, isTrainer]);

  const loadDashboardData = React.useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      // 1. Fetch general platform stats (accessible by everyone)
      const analyticsRes = await api.get<AnalyticsDashboardResponse>("/api/analytics/dashboard");
      setAnalyticsData(analyticsRes);

      // 2. Fetch instance history metrics (accessible by everyone)
      const instanceRes = await api.get<InstanceMetricsPoint[]>("/api/analytics/metrics/instances");
      setInstanceMetrics(instanceRes || []);

      // 3. Fetch billing details (only if Trainer or Admin)
      if (isAdmin || isTrainer) {
        try {
          const billingRes = await api.get<BillingSummaryResponse>("/api/billing/summary");
          setBillingData(billingRes);

          const costRes = await api.get<CostMetricsPoint[]>("/api/analytics/metrics/costs");
          setCostMetrics(costRes || []);
        } catch (billingErr) {
          console.warn("Could not fetch billing/costs dashboard data", billingErr);
        }
      }
    } catch (err: any) {
      console.error("Dashboard metrics loading error:", err);
      setError("Failed to sync latest cloud telemetry data from backend API.");
    } finally {
      setLoading(false);
    }
  }, [api, isAdmin, isTrainer]);

  React.useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  // Format stats cards data
  const statsData = React.useMemo(() => {
    if (!analyticsData) return undefined;
    return {
      activeInstances: analyticsData.active_instances,
      totalStudents: analyticsData.total_users,
      monthlySpend: billingData?.total_platform_cost ?? analyticsData.total_spend_usd,
      budgetLimit: billingData?.monthly_budget ?? 500.0,
      uptimePercent: 100.0, // System health indicator
    };
  }, [analyticsData, billingData]);

  // Format instance metrics for Recharts
  const formattedInstanceData = React.useMemo(() => {
    if (!instanceMetrics || instanceMetrics.length === 0) return [];
    return instanceMetrics.map((p) => {
      const date = new Date(p.timestamp);
      return {
        day: date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        active: p.running_count,
        stopped: p.stopped_count,
      };
    });
  }, [instanceMetrics]);

  // Format cost metrics for Recharts
  const formattedCostData = React.useMemo(() => {
    if (!costMetrics || costMetrics.length === 0) return [];
    return costMetrics.map((p) => {
      const date = new Date(p.timestamp);
      return {
        month: date.toLocaleDateString([], { month: "short", day: "numeric" }),
        compute: p.cumulative_cost_usd,
        storage: 0.0,
        network: 0.0,
      };
    });
  }, [costMetrics]);

  if (loading) {
    return (
      <div className="flex h-[60vh] flex-col items-center justify-center gap-4">
        <RefreshCw className="h-8 w-8 animate-spin text-indigo-500" />
        <p className="text-sm text-zinc-400">Syncing active virtual machine telemetry...</p>
      </div>
    );
  }

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

      {error && (
        <Alert variant="destructive" className="bg-red-500/10 border-red-500/20 text-red-400">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Connection Issue</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Stats Cards Section */}
      <StatsCards data={statsData} />

      {/* Main Charts / Feed Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* Instance Trends */}
        <div className="lg:col-span-2 space-y-6">
          <InstanceChart data={formattedInstanceData} />
          {(isAdmin || isTrainer) && <CostChart data={formattedCostData} />}
        </div>

        {/* Real-time Activity Feed */}
        <div>
          <ActivityFeed />
        </div>
      </div>
    </div>
  );
}

"use client"

import * as React from "react"
import { useApiClient } from "@/hooks/use-api-client"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { UserPlus, Shield, User, Trash2, Search, Users, FolderKanban } from "lucide-react"

interface UserRecord {
  id: string
  name: string
  email: string
  role: "Admin" | "Trainer" | "Student"
  status: "Active" | "Inactive"
}

export default function AdminUsersPage() {
  const api = useApiClient()
  const [users, setUsers] = React.useState<UserRecord[]>([])
  const [groups, setGroups] = React.useState<any[]>([])
  const [search, setSearch] = React.useState("")
  const [loading, setLoading] = React.useState(false)
  const [activeTab, setActiveTab] = React.useState<"trainers" | "students" | "admins">("trainers")

  const fetchData = async () => {
    setLoading(true)
    try {
      const usersData = await api.get<UserRecord[]>("/api/admin/users")
      if (usersData && Array.isArray(usersData)) {
        // Map backend UserSummary model to frontend UserRecord structure
        const mappedUsers = usersData.map((u: any) => ({
          id: u.id,
          name: u.name || "Anonymous",
          email: u.email || "No email",
          role: (u.roles && u.roles[0]) ? u.roles[0] as any : "Student",
          status: "Active" as const
        }))
        setUsers(mappedUsers)
      }
      
      const groupsData = await api.get<any[]>("/api/admin/groups")
      setGroups(groupsData || [])
    } catch (err) {
      console.warn("Could not load users/groups directory from API.", err)
    } finally {
      setLoading(false)
    }
  }

  React.useEffect(() => {
    fetchData()
  }, [])

  const handleRoleChange = async (userId: string, newRole: "Admin" | "Trainer" | "Student") => {
    try {
      await api.post(`/api/admin/users/${userId}/role`, { role: newRole })
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role: newRole } : u))
      )
    } catch (err) {
      console.error("Failed to change user role", err)
    }
  }

  const handleDeleteUser = async (userId: string) => {
    if (!confirm("Are you sure you want to delete this user from the directory?")) return
    try {
      await api.del(`/api/admin/users/${userId}`)
      setUsers((prev) => prev.filter((u) => u.id !== userId))
    } catch (err) {
      console.error("Failed to delete user", err)
    }
  }

  // Filter and search logic
  const filteredUsers = React.useMemo(() => {
    return users.filter(
      (u) =>
        (u.name.toLowerCase().includes(search.toLowerCase()) ||
          u.email.toLowerCase().includes(search.toLowerCase())) &&
        ((activeTab === "trainers" && u.role === "Trainer") ||
          (activeTab === "students" && u.role === "Student") ||
          (activeTab === "admins" && u.role === "Admin"))
    )
  }, [users, search, activeTab])

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-zinc-50">Portal Directory</h1>
          <p className="text-sm text-zinc-400">
            Control platform roles, manage sandbox limits, and audit user records.
          </p>
        </div>
      </div>

      {/* Tabs Selector */}
      <div className="flex border-b border-zinc-800 gap-1">
        <button
          onClick={() => setActiveTab("trainers")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === "trainers"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-zinc-400 hover:text-zinc-200"
          }`}
        >
          Trainers ({users.filter(u => u.role === "Trainer").length})
        </button>
        <button
          onClick={() => setActiveTab("students")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === "students"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-zinc-400 hover:text-zinc-200"
          }`}
        >
          Students ({users.filter(u => u.role === "Student").length})
        </button>
        <button
          onClick={() => setActiveTab("admins")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === "admins"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-zinc-400 hover:text-zinc-200"
          }`}
        >
          Administrators ({users.filter(u => u.role === "Admin").length})
        </button>
      </div>

      <Card className="bg-zinc-950/40 border-zinc-800">
        <CardHeader className="pb-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <CardTitle className="text-base font-semibold text-zinc-50">
              {activeTab === "trainers" && "Training Instructors"}
              {activeTab === "students" && "Cohort Students"}
              {activeTab === "admins" && "Platform Administrators"}
            </CardTitle>
            <CardDescription className="text-xs text-zinc-400">
              {activeTab === "trainers" && "Instructors assigned to manage sandboxes and training groups."}
              {activeTab === "students" && "Students enrolled in cloud training courses."}
              {activeTab === "admins" && "Administrators with full control over settings and directories."}
            </CardDescription>
          </div>
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-zinc-500" />
            <Input
              placeholder={`Search ${activeTab}...`}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 bg-zinc-900 border-zinc-800 text-zinc-50 placeholder:text-zinc-500 focus-visible:ring-indigo-500"
            />
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border border-zinc-800 overflow-hidden">
            <Table>
              <TableHeader className="bg-zinc-900/50">
                <TableRow className="border-b border-zinc-800">
                  <TableHead className="text-zinc-400 font-medium">User</TableHead>
                  <TableHead className="text-zinc-400 font-medium">Email Address</TableHead>
                  <TableHead className="text-zinc-400 font-medium">
                    {activeTab === "trainers" && "Managed Cohorts"}
                    {activeTab === "students" && "Enrolled Cohort"}
                    {activeTab === "admins" && "Identity Scope"}
                  </TableHead>
                  <TableHead className="text-zinc-400 font-medium">Platform Role</TableHead>
                  <TableHead className="text-zinc-400 font-medium text-right">Operations</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-10 text-zinc-500 text-sm">
                      Syncing directory from database...
                    </TableCell>
                  </TableRow>
                ) : filteredUsers.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-10 text-zinc-500 text-sm">
                      No {activeTab} registered on the platform.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredUsers.map((user) => {
                    // Find group mappings
                    const managedGroups = groups.filter((g) => g.trainer_id === user.id)
                    const studentGroup = groups.find((g) => g.student_ids?.includes(user.id))

                    return (
                      <TableRow key={user.id} className="border-b border-zinc-900 hover:bg-zinc-900/20">
                        <TableCell className="font-semibold text-zinc-300">{user.name}</TableCell>
                        <TableCell className="text-zinc-400 font-mono text-xs">{user.email}</TableCell>
                        <TableCell>
                          {activeTab === "trainers" && (
                            managedGroups.length > 0 ? (
                              <div className="flex flex-wrap gap-1">
                                {managedGroups.map(g => (
                                  <span key={g.id} className="text-[10px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-1.5 py-0.5 rounded flex items-center gap-1">
                                    <FolderKanban className="h-3 w-3" />
                                    {g.name}
                                  </span>
                                ))}
                              </div>
                            ) : (
                              <span className="text-xs text-zinc-500 italic">No groups assigned</span>
                            )
                          )}
                          {activeTab === "students" && (
                            studentGroup ? (
                              <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-1.5 py-0.5 rounded inline-flex items-center gap-1">
                                <Users className="h-3 w-3" />
                                {studentGroup.name}
                              </span>
                            ) : (
                              <span className="text-xs text-zinc-500 italic">Unassigned</span>
                            )
                          )}
                          {activeTab === "admins" && (
                            <span className="text-xs font-mono text-zinc-400">Global Admin</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <Select
                            value={user.role}
                            onValueChange={(val) => handleRoleChange(user.id, val as any)}
                          >
                            <SelectTrigger className="w-[120px] h-8 bg-zinc-900 border-zinc-800 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent className="bg-zinc-950 border-zinc-800">
                              <SelectItem value="Admin" className="text-xs">Admin</SelectItem>
                              <SelectItem value="Trainer" className="text-xs">Trainer</SelectItem>
                              <SelectItem value="Student" className="text-xs">Student</SelectItem>
                            </SelectContent>
                          </Select>
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDeleteUser(user.id)}
                            className="h-8 w-8 text-zinc-500 hover:text-red-400 hover:bg-red-500/10"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    )
                  })
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

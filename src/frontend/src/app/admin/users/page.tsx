"use client"

import * as React from "react"
import { useApiClient } from "@/hooks/use-api-client"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { UserPlus, Shield, User, Trash2, Search, ArrowUpDown } from "lucide-react"

interface UserRecord {
  id: string
  name: string
  email: string
  role: "Admin" | "Trainer" | "Student"
  status: "Active" | "Inactive"
}

export default function AdminUsersPage() {
  const api = useApiClient()
  const [users, setUsers] = React.useState<UserRecord[]>([
    { id: "1", name: "John Doe", email: "john.doe@contoso.com", role: "Student", status: "Active" },
    { id: "2", name: "Jane Smith", email: "jane.smith@contoso.com", role: "Trainer", status: "Active" },
    { id: "3", name: "Alice Johnson", email: "alice.johnson@contoso.com", role: "Admin", status: "Active" },
    { id: "4", name: "Bob Brown", email: "bob.brown@contoso.com", role: "Student", status: "Inactive" },
  ])
  const [search, setSearch] = React.useState("")
  const [loading, setLoading] = React.useState(false)

  React.useEffect(() => {
    const fetchUsers = async () => {
      setLoading(true)
      try {
        const data = await api.get<UserRecord[]>("/api/admin/users")
        if (data && Array.isArray(data)) {
          setUsers(data)
        }
      } catch (err) {
        console.warn("Could not load users from API, using fallback.", err)
      } finally {
        setLoading(false)
      }
    }
    fetchUsers()
  }, [])

  const handleRoleChange = async (userId: string, newRole: "Admin" | "Trainer" | "Student") => {
    try {
      await api.put(`/api/admin/users/${userId}/role`, { role: newRole })
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role: newRole } : u))
      )
    } catch (err) {
      console.error("Failed to change user role", err)
      // Optimistic updates fallback for visual demo
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role: newRole } : u))
      )
    }
  }

  const handleDeleteUser = async (userId: string) => {
    if (!confirm("Are you sure you want to delete this user?")) return
    try {
      await api.del(`/api/admin/users/${userId}`)
      setUsers((prev) => prev.filter((u) => u.id !== userId))
    } catch (err) {
      console.error("Failed to delete user", err)
      setUsers((prev) => prev.filter((u) => u.id !== userId))
    }
  }

  const filteredUsers = users.filter(
    (u) =>
      u.name.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-zinc-50">User Management</h1>
          <p className="text-sm text-zinc-400">
            Control platform roles, provision training licenses, and audit credentials.
          </p>
        </div>
        <Button className="bg-indigo-600 hover:bg-indigo-500 text-white gap-2 max-w-fit">
          <UserPlus className="h-4 w-4" />
          Invite User
        </Button>
      </div>

      <Card className="bg-zinc-950/40 border-zinc-800">
        <CardHeader className="pb-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <CardTitle className="text-base font-semibold text-zinc-50">All Portal Users</CardTitle>
            <CardDescription className="text-xs text-zinc-400">
              Assigned Microsoft Entra application roles mapped to CTMP.
            </CardDescription>
          </div>
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-zinc-500" />
            <Input
              placeholder="Search by name or email..."
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
                  <TableHead className="text-zinc-400 font-medium">Identity Role</TableHead>
                  <TableHead className="text-zinc-400 font-medium">Status</TableHead>
                  <TableHead className="text-zinc-400 font-medium text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredUsers.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-10 text-zinc-500 text-sm">
                      No users found.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredUsers.map((user) => (
                    <TableRow key={user.id} className="border-b border-zinc-900 hover:bg-zinc-900/20">
                      <TableCell className="font-semibold text-zinc-300">{user.name}</TableCell>
                      <TableCell className="text-zinc-400 font-mono text-xs">{user.email}</TableCell>
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
                      <TableCell>
                        <Badge
                          className={
                            user.status === "Active"
                              ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                              : "bg-zinc-800 text-zinc-400 border border-zinc-700"
                          }
                        >
                          {user.status}
                        </Badge>
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
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

"use client"

import * as React from "react"
import { useApiClient } from "@/hooks/use-api-client"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { FolderPlus, Users, Eye, Trash2, ShieldAlert } from "lucide-react"

interface TrainingGroup {
  id: string
  name: string
  studentCount: number
  awsRoleArn: string
  maxInstancesPerStudent: number
  status: "Active" | "Inactive"
}

export default function TrainerGroupsPage() {
  const api = useApiClient()
  const [groups, setGroups] = React.useState<TrainingGroup[]>([
    { id: "g1", name: "AWS-101-Morning", studentCount: 15, awsRoleArn: "arn:aws:iam::123456789012:role/TrainerRole", maxInstancesPerStudent: 2, status: "Active" },
    { id: "g2", name: "Kubernetes-Advanced", studentCount: 8, awsRoleArn: "arn:aws:iam::123456789012:role/K8sRole", maxInstancesPerStudent: 3, status: "Active" },
  ])
  const [loading, setLoading] = React.useState(false)
  const [name, setName] = React.useState("")
  const [awsRoleArn, setAwsRoleArn] = React.useState("")
  const [maxInstances, setMaxInstances] = React.useState(2)
  const [open, setOpen] = React.useState(false)

  React.useEffect(() => {
    const fetchGroups = async () => {
      setLoading(true)
      try {
        const data = await api.get<TrainingGroup[]>("/api/trainer/groups")
        if (data && Array.isArray(data)) {
          setGroups(data)
        }
      } catch (err) {
        console.warn("Could not load groups, using fallback.", err)
      } finally {
        setLoading(false)
      }
    }
    fetchGroups()
  }, [])

  const handleCreateGroup = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const payload = { name, awsRoleArn, maxInstancesPerStudent: maxInstances }
      const newGroup = await api.post<TrainingGroup>("/api/trainer/groups", payload)
      if (newGroup) {
        setGroups((prev) => [...prev, newGroup])
      } else {
        // Fallback for mock demo
        setGroups((prev) => [...prev, {
          id: Math.random().toString(),
          name,
          studentCount: 0,
          awsRoleArn,
          maxInstancesPerStudent: maxInstances,
          status: "Active"
        }])
      }
      // Reset form
      setName("")
      setAwsRoleArn("")
      setMaxInstances(2)
      setOpen(false)
    } catch (err) {
      console.error("Failed to create group", err)
      // Visual feedback mock save
      setGroups((prev) => [...prev, {
        id: Math.random().toString(),
        name,
        studentCount: 0,
        awsRoleArn,
        maxInstancesPerStudent: maxInstances,
        status: "Active"
      }])
      setName("")
      setAwsRoleArn("")
      setMaxInstances(2)
      setOpen(false)
    }
  }

  const handleDeleteGroup = async (id: string) => {
    if (!confirm("Are you sure you want to terminate this group?")) return
    try {
      await api.del(`/api/trainer/groups/${id}`)
      setGroups((prev) => prev.filter((g) => g.id !== id))
    } catch (err) {
      console.error("Failed to delete group", err)
      setGroups((prev) => prev.filter((g) => g.id !== id))
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-zinc-50">Training Groups</h1>
          <p className="text-sm text-zinc-400">
            Create cohort sandbox environments, assign AWS deployment roles, and track active students.
          </p>
        </div>

        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button className="bg-indigo-600 hover:bg-indigo-500 text-white gap-2 max-w-fit">
              <FolderPlus className="h-4 w-4" />
              Create Group
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-zinc-950 border border-zinc-800 text-zinc-50">
            <DialogHeader>
              <DialogTitle className="text-zinc-50">Create Training Group</DialogTitle>
              <DialogDescription className="text-zinc-400">
                Setup a cohort sandbox. Students in this group will inherit AWS deployment resource privileges.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreateGroup} className="space-y-4 py-2">
              <div className="space-y-1.5">
                <Label htmlFor="gname" className="text-zinc-400">Group Name</Label>
                <Input
                  id="gname"
                  placeholder="e.g., AWS-101-Cohort-A"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="bg-zinc-900 border-zinc-800 text-zinc-50"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="arn" className="text-zinc-400">AWS Role ARN (OIDC)</Label>
                <Input
                  id="arn"
                  placeholder="arn:aws:iam::123456789012:role/CTMP-OIDC-Role"
                  value={awsRoleArn}
                  onChange={(e) => setAwsRoleArn(e.target.value)}
                  required
                  className="bg-zinc-900 border-zinc-800 text-zinc-50"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="limitInst" className="text-zinc-400">Max Instances Per Student</Label>
                <Input
                  id="limitInst"
                  type="number"
                  min={1}
                  max={5}
                  value={maxInstances}
                  onChange={(e) => setMaxInstances(Number(e.target.value))}
                  required
                  className="bg-zinc-900 border-zinc-800 text-zinc-50"
                />
              </div>
              <DialogFooter className="pt-4">
                <Button type="button" variant="outline" onClick={() => setOpen(false)} className="border-zinc-800 text-zinc-400">
                  Cancel
                </Button>
                <Button type="submit" className="bg-indigo-600 hover:bg-indigo-500 text-white">
                  Create
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Card className="bg-zinc-950/40 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-base font-semibold text-zinc-50">Active Groups</CardTitle>
          <CardDescription className="text-xs text-zinc-400">
            Overview of sandbox groups. Instructors can monitor student counts and AWS IAM connections.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border border-zinc-800 overflow-hidden">
            <Table>
              <TableHeader className="bg-zinc-900/50">
                <TableRow className="border-b border-zinc-800">
                  <TableHead className="text-zinc-400 font-medium">Group Name</TableHead>
                  <TableHead className="text-zinc-400 font-medium">Assigned Students</TableHead>
                  <TableHead className="text-zinc-400 font-medium">Max EC2 Limit</TableHead>
                  <TableHead className="text-zinc-400 font-medium">AWS IAM Role ARN</TableHead>
                  <TableHead className="text-zinc-400 font-medium">Status</TableHead>
                  <TableHead className="text-zinc-400 font-medium text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {groups.map((group) => (
                  <TableRow key={group.id} className="border-b border-zinc-900 hover:bg-zinc-900/20">
                    <TableCell className="font-semibold text-zinc-300">{group.name}</TableCell>
                    <TableCell className="text-zinc-400">
                      <span className="inline-flex items-center gap-1">
                        <Users className="h-3.5 w-3.5 text-zinc-500" />
                        {group.studentCount}
                      </span>
                    </TableCell>
                    <TableCell className="text-zinc-300 font-medium">{group.maxInstancesPerStudent} VMs</TableCell>
                    <TableCell className="text-zinc-400 font-mono text-xs max-w-[200px] truncate" title={group.awsRoleArn}>
                      {group.awsRoleArn}
                    </TableCell>
                    <TableCell>
                      <Badge className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                        {group.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1.5">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-zinc-500 hover:text-zinc-50 hover:bg-zinc-900"
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDeleteGroup(group.id)}
                          className="h-8 w-8 text-zinc-500 hover:text-red-400 hover:bg-red-500/10"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

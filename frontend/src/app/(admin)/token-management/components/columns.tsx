"use client"

import { ColumnDef, Row } from "@tanstack/react-table"
import type { UserWithTokenLimits } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
// import { Checkbox } from "@/components/ui/checkbox" // 必要であれば選択用チェックボックス
// import { ArrowUpDown } from "lucide-react" // ソートアイコン用

export const columns: ColumnDef<UserWithTokenLimits>[] = [
  // TODO: 必要であれば選択用チェックボックスカラム
  // {
  //   id: "select",
  //   header: ({ table }) => (
  //     <Checkbox
  //       checked={table.getIsAllPageRowsSelected()}
  //       onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
  //       aria-label="Select all"
  //     />
  //   ),
  //   cell: ({ row }) => (
  //     <Checkbox
  //       checked={row.getIsSelected()}
  //       onCheckedChange={(value) => row.toggleSelected(!!value)}
  //       aria-label="Select row"
  //     />
  //   ),
  //   enableSorting: false,
  //   enableHiding: false,
  // },
  {
    accessorKey: "id",
    header: "ID",
  },
  {
    accessorKey: "email",
    header: "Email",
    // TODO: ソートを追加する場合
    // header: ({ column }) => {
    //   return (
    //     <Button
    //       variant="ghost"
    //       onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
    //     >
    //       Email
    //       <ArrowUpDown className="ml-2 h-4 w-4" />
    //     </Button>
    //   )
    // },
  },
  {
    accessorKey: "is_active",
    header: "Status",
    cell: ({ row }: { row: Row<UserWithTokenLimits> }) => {
      const isActive = row.getValue("is_active")
      return (
        <Badge 
          variant={isActive ? "default" : "destructive"}
          className={isActive ? "bg-green-100 text-green-800 border-green-200" : "bg-red-100 text-red-800 border-red-200"}
        >
          {isActive ? "Active" : "Inactive"}
        </Badge>
      )
    },
  },
  {
    accessorKey: "is_verified",
    header: "Verified",
    cell: ({ row }: { row: Row<UserWithTokenLimits> }) => {
      const isVerified = row.getValue("is_verified")
      return (
        <Badge 
          variant={isVerified ? "default" : "secondary"}
          className={isVerified ? "bg-blue-100 text-blue-800 border-blue-200" : "bg-gray-100 text-gray-800 border-gray-200"}
        >
          {isVerified ? "Verified" : "Unverified"}
        </Badge>
      )
    },
  },
  {
    id: "token_limits",
    header: "Token Limits",
    cell: ({ row }: { row: Row<UserWithTokenLimits> }) => {
      const tokenLimits = row.original.token_limits;
      if (!tokenLimits || tokenLimits.length === 0) {
        return <span className="text-xs text-muted-foreground">None</span>;
      }
      return (
        <ul className="list-disc pl-4 text-xs">
          {tokenLimits.map((limit) => (
            <li key={limit.id}>
              {`${limit.model_name}: ${limit.limit_value} / ${limit.period_value} ${limit.period_unit}`}
            </li>
          ))}
        </ul>
      );
    },
  },
  {
    id: "actions",
    header: "Actions",
    cell: ({ row }: { row: Row<UserWithTokenLimits> }) => {
      const user = row.original;
      return (
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => console.log("Edit user:", user.email)} // TODO: 編集処理を実装
          >
            Edit
          </Button>
        </div>
      );
    },
  },
  // TODO: アクションカラム (編集ボタンなど) を追加
] 

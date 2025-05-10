"use client"

import { ColumnDef, Row } from "@tanstack/react-table"
import type { UserWithTokenLimits } from "@/lib/types"
import { Button } from "@/components/ui/button"
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
    accessorKey: "is_admin",
    header: "Admin",
    cell: ({ row }: { row: Row<UserWithTokenLimits> }) => {
      const isAdmin = row.getValue("is_admin")
      return isAdmin ? "Yes" : "No"
    },
  },
  {
    accessorKey: "is_verified",
    header: "Verified",
    cell: ({ row }: { row: Row<UserWithTokenLimits> }) => {
      const isVerified = row.getValue("is_verified")
      return isVerified ? "Yes" : "No"
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
        <Button
          variant="outline"
          size="sm"
          onClick={() => console.log("Edit user:", user.email)} // TODO: 編集処理を実装
        >
          Edit Limits
        </Button>
      );
    },
  },
  // TODO: アクションカラム (編集ボタンなど) を追加
] 

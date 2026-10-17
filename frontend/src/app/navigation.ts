import {
  FileCheck,
  FileText,
  FolderSearch,
  LayoutDashboard,
  Network,
  Settings,
  type LucideIcon,
} from 'lucide-react'

export type NavItem = {
  to: string
  label: string
  icon: LucideIcon
  end?: boolean
}

export const navItems: NavItem[] = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/verify', label: 'Verify Invoice', icon: FileCheck },
  { to: '/network', label: 'Network Explorer', icon: Network },
  { to: '/investigations', label: 'Investigations', icon: FolderSearch },
  { to: '/evidence', label: 'Evidence and Reports', icon: FileText },
  { to: '/settings', label: 'Settings', icon: Settings },
]

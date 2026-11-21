export const navigationItems = [
  { href: "/", label: "Transactions", permission: "transactions.read", icon: "TX" },
  { href: "/fraud", label: "Fraud Monitoring", permission: "fraud.read", icon: "FR" },
  { href: "/cases", label: "Investigations", permission: "cases.read", icon: "CA" },
  { href: "/decisions", label: "Decisions", permission: "decisions.read", icon: "DE" },
  { href: "/security", label: "Security Operations", permission: "security.monitor", icon: "SE" },
] as const;

export function visibleNavigation(permissions: string[]) {
  return navigationItems.filter(item =>
    permissions.includes("*") || permissions.includes(item.permission)
  );
}

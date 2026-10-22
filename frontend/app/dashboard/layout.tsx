import DashboardShell from "../../components/dashboard-shell";

export default function DashboardLayout(props: LayoutProps<"/dashboard">) {
  return <DashboardShell>{props.children}</DashboardShell>;
}

// This layout makes the DashboardShell component wrap around all child routes under /dashboard.
// Any routes rendered under /dashboard will appear inside the DashboardShell, with the child content rendered within it.
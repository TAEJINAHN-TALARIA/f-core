import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: string;
  sub?: string;
  positive?: boolean | null;
}

export default function MetricCard({ label, value, sub, positive }: MetricCardProps) {
  return (
    <Card className="bg-card border-border hover:border-blue-500/40 hover:-translate-y-0.5 transition-all duration-300 shadow-md hover:shadow-blue-950/20">
      <CardContent className="p-5">
        <p className="text-muted-foreground text-xs font-semibold uppercase tracking-wider mb-2">{label}</p>
        <p
          className={cn(
            "text-2xl font-bold tracking-tight",
            positive === true ? "text-emerald-400" : positive === false ? "text-red-400" : "text-foreground"
          )}
        >
          {value}
        </p>
        {sub && <p className="text-gray-500 text-xs mt-1">{sub}</p>}
      </CardContent>
    </Card>
  );
}

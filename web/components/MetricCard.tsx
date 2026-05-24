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
    <Card className="bg-gray-900 border-gray-800">
      <CardContent className="p-4">
        <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">{label}</p>
        <p
          className={cn(
            "text-xl font-bold",
            positive === true ? "text-emerald-400" : positive === false ? "text-red-400" : "text-white"
          )}
        >
          {value}
        </p>
        {sub && <p className="text-gray-500 text-xs mt-0.5">{sub}</p>}
      </CardContent>
    </Card>
  );
}

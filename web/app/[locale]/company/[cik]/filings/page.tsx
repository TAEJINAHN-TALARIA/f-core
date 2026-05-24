import { getFilings } from "@/lib/api";
import FilingsTable from "@/components/FilingsTable";

export default async function FilingsPage({ params }: { params: Promise<{ cik: string }> }) {
  const { cik } = await params;
  const data = await getFilings(cik, 30);

  return (
    <div className="rounded-xl border border-gray-800 overflow-hidden">
      <FilingsTable filings={data.data} />
    </div>
  );
}

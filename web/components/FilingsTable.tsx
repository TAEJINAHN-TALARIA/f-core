import { getTranslations } from "next-intl/server";
import type { Filing } from "@/lib/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

interface Props {
  filings: Filing[];
}

function edgarUrl(cik: string, form: string) {
  const paddedCik = cik.replace(/^0+/, "");
  return `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${paddedCik}&type=${encodeURIComponent(form)}&dateb=&owner=include&count=10`;
}

const FORM_COLORS: Record<string, string> = {
  "10-K": "bg-blue-950/60 text-blue-400 border-blue-800",
  "10-K/A": "bg-blue-950/40 text-blue-300 border-blue-900",
  "10-Q": "bg-violet-950/60 text-violet-400 border-violet-800",
  "10-Q/A": "bg-violet-950/40 text-violet-300 border-violet-900",
};

export default async function FilingsTable({ filings }: Props) {
  const t = await getTranslations("filings");
  const tc = await getTranslations("company");

  if (!filings.length) {
    return <p className="text-gray-500 text-sm">{tc("noData")}</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow className="border-gray-700 bg-gray-900 hover:bg-gray-900">
          <TableHead className="text-gray-300 font-semibold w-24">{t("form")}</TableHead>
          <TableHead className="text-gray-300 font-semibold">{t("filedDate")}</TableHead>
          <TableHead className="text-gray-300 font-semibold">{t("periodEnd")}</TableHead>
          <TableHead className="text-gray-300 font-semibold text-right">{t("viewOnEdgar")}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {filings.map((f, i) => (
          <TableRow key={i} className="border-gray-800 hover:bg-gray-800/60">
            <TableCell>
              <Badge
                variant="outline"
                className={`font-mono text-xs ${FORM_COLORS[f.form] ?? "text-gray-400 border-gray-700"}`}
              >
                {f.form}
              </Badge>
            </TableCell>
            <TableCell className="text-gray-100 font-mono text-sm">{f.filed_date ?? "—"}</TableCell>
            <TableCell className="text-gray-100 font-mono text-sm">{f.end_date}</TableCell>
            <TableCell className="text-right">
              <a
                href={edgarUrl(f.cik, f.form)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-400 hover:text-blue-200 transition-colors text-sm font-medium"
              >
                ↗ EDGAR
              </a>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

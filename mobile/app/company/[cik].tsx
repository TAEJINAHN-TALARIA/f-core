import { useEffect, useState } from "react";
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  Linking,
} from "react-native";
import { useLocalSearchParams, useNavigation } from "expo-router";
import {
  getCompany,
  getTTM,
  getMetrics,
  getFilings,
  formatValue,
  formatPercent,
  type Company,
  type TTMResponse,
  type MetricPoint,
  type Filing,
} from "../../lib/api";
import { addToWatchlist, removeFromWatchlist, getWatchlist } from "../(tabs)/watchlist";
import i18n from "../../lib/i18n";

function MetricCard({ label, value, positive }: { label: string; value: string; positive?: boolean | null }) {
  return (
    <View style={styles.card}>
      <Text style={styles.cardLabel}>{label}</Text>
      <Text style={[styles.cardValue, positive === true ? styles.positive : positive === false ? styles.negative : {}]}>
        {value}
      </Text>
    </View>
  );
}

export default function CompanyDetailScreen() {
  const { cik } = useLocalSearchParams<{ cik: string }>();
  const navigation = useNavigation();

  const [company, setCompany] = useState<Company | null>(null);
  const [ttm, setTtm] = useState<TTMResponse | null>(null);
  const [metrics, setMetrics] = useState<MetricPoint[]>([]);
  const [filings, setFilings] = useState<Filing[]>([]);
  const [loading, setLoading] = useState(true);
  const [inWatchlist, setInWatchlist] = useState(false);

  useEffect(() => {
    if (!cik) return;
    setLoading(true);
    Promise.allSettled([
      getCompany(cik),
      getTTM(cik),
      getMetrics(cik, "quarterly"),
      getFilings(cik, 10),
    ]).then(([co, t, m, f]) => {
      if (co.status === "fulfilled") {
        setCompany(co.value);
        navigation.setOptions({ title: co.value.ticker ?? co.value.name });
      }
      if (t.status === "fulfilled") setTtm(t.value);
      if (m.status === "fulfilled") setMetrics(m.value.data);
      if (f.status === "fulfilled") setFilings(f.value.data);
      setLoading(false);
    });

    getWatchlist().then((list) => setInWatchlist(list.some((i) => i.cik === cik)));
  }, [cik]);

  async function toggleWatchlist() {
    if (!company) return;
    if (inWatchlist) {
      await removeFromWatchlist(cik);
      setInWatchlist(false);
    } else {
      await addToWatchlist({ cik, name: company.name, ticker: company.ticker });
      setInWatchlist(true);
    }
  }

  function getTTMValue(tag: string) {
    return ttm?.items.find((i) => i.tag === tag)?.value ?? null;
  }

  function getLatestMetric(metric: string) {
    const sorted = metrics.filter((m) => m.metric === metric).sort((a, b) => b.end_date.localeCompare(a.end_date));
    return sorted[0]?.value ?? null;
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color="#3b82f6" size="large" />
      </View>
    );
  }

  if (!company) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>Company not found</Text>
      </View>
    );
  }

  const revenue = getTTMValue("Revenues") ?? getTTMValue("RevenueFromContractWithCustomerExcludingAssessedTax");
  const netIncome = getTTMValue("NetIncomeLoss");
  const eps = getTTMValue("EarningsPerShareDiluted");
  const grossMargin = getLatestMetric("gross_margin");
  const netMargin = getLatestMetric("net_margin");
  const roe = getLatestMetric("roe");

  const cards = [
    { label: `${i18n.t("metrics.revenue")} (${i18n.t("period.ttm")})`, value: revenue != null ? formatValue(revenue, "USD") : "—" },
    { label: `${i18n.t("metrics.netIncome")} (${i18n.t("period.ttm")})`, value: netIncome != null ? formatValue(netIncome, "USD") : "—", positive: netIncome != null ? netIncome >= 0 : null },
    { label: `${i18n.t("metrics.eps")} (${i18n.t("period.ttm")})`, value: eps != null ? formatValue(eps, "USD/shares") : "—", positive: eps != null ? eps >= 0 : null },
    { label: i18n.t("metrics.grossMargin"), value: grossMargin != null ? formatPercent(grossMargin) : "—" },
    { label: i18n.t("metrics.netMargin"), value: netMargin != null ? formatPercent(netMargin) : "—", positive: netMargin != null ? netMargin >= 0 : null },
    { label: i18n.t("metrics.roe"), value: roe != null ? formatPercent(roe) : "—", positive: roe != null ? roe >= 0 : null },
  ];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Text style={styles.companyName}>{company.name}</Text>
          <View style={styles.badges}>
            {company.ticker && <Text style={styles.ticker}>{company.ticker}</Text>}
            {company.exchange && <Text style={styles.exchange}>{company.exchange}</Text>}
          </View>
          {company.sic_description && (
            <Text style={styles.sector}>{company.sic_description}</Text>
          )}
        </View>
        <TouchableOpacity onPress={toggleWatchlist} style={[styles.watchBtn, inWatchlist && styles.watchBtnActive]}>
          <Text style={[styles.watchBtnText, inWatchlist && styles.watchBtnTextActive]}>
            {inWatchlist ? "★" : "☆"}
          </Text>
        </TouchableOpacity>
      </View>

      {/* TTM Metric Cards */}
      <Text style={styles.sectionTitle}>{i18n.t("company.overview")}</Text>
      <View style={styles.grid}>
        {cards.map((card) => (
          <MetricCard key={card.label} {...card} />
        ))}
      </View>
      {ttm?.as_of && (
        <Text style={styles.ttmNote}>{i18n.t("company.ttmNote")} · as of {ttm.as_of}</Text>
      )}

      {/* Recent Filings */}
      {filings.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{i18n.t("company.filings")}</Text>
          {filings.map((f, i) => {
            const cikNum = f.cik.replace(/^0+/, "");
            const url = `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${cikNum}&type=${encodeURIComponent(f.form)}&dateb=&owner=include&count=10`;
            return (
              <TouchableOpacity key={i} style={styles.filing} onPress={() => Linking.openURL(url)}>
                <Text style={styles.filingForm}>{f.form}</Text>
                <View style={styles.filingInfo}>
                  <Text style={styles.filingDate}>{f.filed_date ?? "—"}</Text>
                  <Text style={styles.filingPeriod}>{f.end_date}</Text>
                </View>
                <Text style={styles.filingArrow}>↗</Text>
              </TouchableOpacity>
            );
          })}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#030712" },
  content: { padding: 16, paddingBottom: 40 },
  center: { flex: 1, backgroundColor: "#030712", alignItems: "center", justifyContent: "center" },
  errorText: { color: "#6b7280", fontSize: 16 },

  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 },
  headerLeft: { flex: 1 },
  companyName: { color: "#f9fafb", fontSize: 20, fontWeight: "bold", marginBottom: 4 },
  badges: { flexDirection: "row", gap: 8, marginBottom: 4 },
  ticker: { color: "#3b82f6", fontFamily: "monospace", fontWeight: "bold", fontSize: 14 },
  exchange: { color: "#6b7280", fontSize: 13 },
  sector: { color: "#9ca3af", fontSize: 12 },

  watchBtn: { padding: 10, borderRadius: 8, borderWidth: 1, borderColor: "#374151" },
  watchBtnActive: { borderColor: "#fbbf24", backgroundColor: "#1f1007" },
  watchBtnText: { fontSize: 20, color: "#6b7280" },
  watchBtnTextActive: { color: "#fbbf24" },

  sectionTitle: { color: "#9ca3af", fontSize: 13, fontWeight: "600", marginBottom: 10, textTransform: "uppercase", letterSpacing: 0.5 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 10, marginBottom: 8 },
  card: { backgroundColor: "#111827", borderRadius: 12, padding: 12, borderWidth: 1, borderColor: "#1f2937", width: "47%" },
  cardLabel: { color: "#6b7280", fontSize: 11, marginBottom: 4 },
  cardValue: { color: "#f9fafb", fontSize: 16, fontWeight: "bold" },
  positive: { color: "#34d399" },
  negative: { color: "#f87171" },
  ttmNote: { color: "#4b5563", fontSize: 11, marginBottom: 20 },

  section: { marginTop: 12 },
  filing: { flexDirection: "row", alignItems: "center", paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: "#1f2937" },
  filingForm: { color: "#3b82f6", fontFamily: "monospace", fontWeight: "bold", width: 52, fontSize: 13 },
  filingInfo: { flex: 1 },
  filingDate: { color: "#d1d5db", fontSize: 13 },
  filingPeriod: { color: "#6b7280", fontSize: 11 },
  filingArrow: { color: "#3b82f6", fontSize: 14 },
});

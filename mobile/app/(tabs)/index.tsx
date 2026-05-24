import { useState, useCallback, useRef } from "react";
import {
  View,
  Text,
  TextInput,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { searchCompanies, type Company } from "../../lib/api";
import i18n from "../../lib/i18n";

export default function SearchScreen() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Company[]>([]);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const search = useCallback(async (q: string) => {
    if (q.trim().length < 1) {
      setResults([]);
      return;
    }
    setLoading(true);
    try {
      const data = await searchCompanies(q.trim());
      setResults(data);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  function handleChange(text: string) {
    setQuery(text);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => search(text), 300);
  }

  function navigate(company: Company) {
    router.push(`/company/${company.cik}`);
  }

  return (
    <View style={styles.container}>
      <View style={styles.searchRow}>
        <TextInput
          value={query}
          onChangeText={handleChange}
          placeholder={i18n.t("home.searchPlaceholder")}
          placeholderTextColor="#6b7280"
          style={styles.input}
          autoCorrect={false}
          autoCapitalize="none"
        />
        {loading && <ActivityIndicator color="#3b82f6" style={styles.spinner} />}
      </View>

      <FlatList
        data={results}
        keyExtractor={(item) => item.cik}
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.result} onPress={() => navigate(item)}>
            <Text style={styles.ticker}>{item.ticker ?? "—"}</Text>
            <View style={styles.resultInfo}>
              <Text style={styles.name} numberOfLines={1}>{item.name}</Text>
              {item.exchange && (
                <Text style={styles.exchange}>{item.exchange}</Text>
              )}
            </View>
          </TouchableOpacity>
        )}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
        ListEmptyComponent={
          query.length > 0 && !loading ? (
            <Text style={styles.empty}>{i18n.t("home.noResults")}</Text>
          ) : null
        }
        contentContainerStyle={styles.listContent}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#030712" },
  searchRow: {
    flexDirection: "row",
    alignItems: "center",
    margin: 16,
    backgroundColor: "#111827",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#1f2937",
    paddingHorizontal: 14,
  },
  input: {
    flex: 1,
    color: "#f9fafb",
    fontSize: 16,
    paddingVertical: 12,
  },
  spinner: { marginLeft: 8 },
  result: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 12,
  },
  ticker: {
    color: "#3b82f6",
    fontFamily: "monospace",
    fontWeight: "bold",
    fontSize: 14,
    width: 52,
  },
  resultInfo: { flex: 1 },
  name: { color: "#f9fafb", fontSize: 14 },
  exchange: { color: "#6b7280", fontSize: 12, marginTop: 2 },
  separator: { height: 1, backgroundColor: "#1f2937", marginLeft: 16 },
  empty: { color: "#6b7280", textAlign: "center", marginTop: 32, fontSize: 14 },
  listContent: { paddingBottom: 20 },
});

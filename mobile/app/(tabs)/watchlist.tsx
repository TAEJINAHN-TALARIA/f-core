import { useEffect, useState } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useRouter, useFocusEffect } from "expo-router";
import { useCallback } from "react";
import i18n from "../../lib/i18n";

interface WatchlistItem {
  cik: string;
  name: string;
  ticker: string | null;
}

const STORAGE_KEY = "@fcore_watchlist";

export async function getWatchlist(): Promise<WatchlistItem[]> {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export async function addToWatchlist(item: WatchlistItem): Promise<void> {
  const list = await getWatchlist();
  if (!list.find((i) => i.cik === item.cik)) {
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify([...list, item]));
  }
}

export async function removeFromWatchlist(cik: string): Promise<void> {
  const list = await getWatchlist();
  await AsyncStorage.setItem(
    STORAGE_KEY,
    JSON.stringify(list.filter((i) => i.cik !== cik))
  );
}

export default function WatchlistScreen() {
  const [list, setList] = useState<WatchlistItem[]>([]);
  const router = useRouter();

  useFocusEffect(
    useCallback(() => {
      getWatchlist().then(setList);
    }, [])
  );

  async function remove(cik: string) {
    await removeFromWatchlist(cik);
    setList((prev) => prev.filter((i) => i.cik !== cik));
  }

  if (list.length === 0) {
    return (
      <View style={styles.emptyContainer}>
        <Text style={styles.emptyText}>{i18n.t("watchlist.empty")}</Text>
      </View>
    );
  }

  return (
    <FlatList
      data={list}
      keyExtractor={(item) => item.cik}
      renderItem={({ item }) => (
        <View style={styles.row}>
          <TouchableOpacity
            style={styles.info}
            onPress={() => router.push(`/company/${item.cik}`)}
          >
            <Text style={styles.ticker}>{item.ticker ?? "—"}</Text>
            <Text style={styles.name} numberOfLines={1}>{item.name}</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => remove(item.cik)} style={styles.removeBtn}>
            <Text style={styles.removeText}>{i18n.t("watchlist.remove")}</Text>
          </TouchableOpacity>
        </View>
      )}
      ItemSeparatorComponent={() => <View style={styles.separator} />}
      contentContainerStyle={styles.listContent}
      style={styles.container}
    />
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#030712" },
  emptyContainer: {
    flex: 1,
    backgroundColor: "#030712",
    alignItems: "center",
    justifyContent: "center",
    padding: 32,
  },
  emptyText: { color: "#6b7280", textAlign: "center", lineHeight: 22, fontSize: 14 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  info: { flex: 1, flexDirection: "row", alignItems: "center", gap: 12 },
  ticker: { color: "#3b82f6", fontFamily: "monospace", fontWeight: "bold", fontSize: 14, width: 52 },
  name: { color: "#f9fafb", fontSize: 14, flex: 1 },
  removeBtn: { padding: 8 },
  removeText: { color: "#ef4444", fontSize: 13 },
  separator: { height: 1, backgroundColor: "#1f2937", marginLeft: 16 },
  listContent: { paddingBottom: 20 },
});

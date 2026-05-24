import { Tabs } from "expo-router";
import i18n from "../../lib/i18n";

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarStyle: { backgroundColor: "#111827", borderTopColor: "#1f2937" },
        tabBarActiveTintColor: "#3b82f6",
        tabBarInactiveTintColor: "#6b7280",
        headerStyle: { backgroundColor: "#030712" },
        headerTintColor: "#f9fafb",
      }}
    >
      <Tabs.Screen
        name="index"
        options={{ title: i18n.t("tabs.search") }}
      />
      <Tabs.Screen
        name="watchlist"
        options={{ title: i18n.t("tabs.watchlist") }}
      />
    </Tabs>
  );
}

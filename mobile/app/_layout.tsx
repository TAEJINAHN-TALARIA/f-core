import { Stack } from "expo-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StatusBar } from "expo-status-bar";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 5 * 60 * 1000 } },
});

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: "#030712" },
          headerTintColor: "#f9fafb",
          headerTitleStyle: { fontWeight: "bold" },
          contentStyle: { backgroundColor: "#030712" },
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen
          name="company/[cik]"
          options={{ title: "Company" }}
        />
      </Stack>
    </QueryClientProvider>
  );
}

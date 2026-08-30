import { Redirect } from "expo-router";
import { ActivityIndicator, View } from "react-native";

import { useAuth } from "@/src/context/AuthContext";
import { useTheme } from "@/src/theme/ThemeContext";

export default function Index() {
  const { user, loading } = useAuth();
  const { colors } = useTheme();

  if (loading) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.bg, alignItems: "center", justifyContent: "center" }}>
        <ActivityIndicator color={colors.accentTeal} />
      </View>
    );
  }

  if (!user) return <Redirect href="/welcome" />;
  if (!user.onboarded) return <Redirect href="/onboarding" />;
  if (!user.base_photo_path) return <Redirect href="/photo" />;
  if (!user.has_targets) return <Redirect href="/generating" />;
  if (!user.has_plan) return <Redirect href="/targets" />;
  return <Redirect href="/(tabs)" />;
}

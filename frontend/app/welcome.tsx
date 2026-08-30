import { useRouter } from "expo-router";
import { Text, View } from "react-native";
import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";

import { useTheme } from "@/src/theme/ThemeContext";
import { GradientButton, Label, Screen } from "@/src/components/ui";

export default function Welcome() {
  const router = useRouter();
  const { colors, spacing, font } = useTheme();
  const insets = useSafeAreaInsets();

  const points = [
    { icon: "target" as const, text: "A realistic future self — bounded by your age, sex, frame & health." },
    { icon: "activity" as const, text: "A diet & training plan that respects your conditions and timeline." },
    { icon: "shield" as const, text: "Private by default. Your photos, encrypted, deletable anytime." },
  ];

  return (
    <Screen>
      <View style={{ flex: 1, paddingTop: insets.top + spacing.xl, paddingHorizontal: spacing.lg, paddingBottom: insets.bottom + spacing.md }}>
        <View style={{ flex: 1, justifyContent: "center" }}>
          <Label>The anti–fantasy-filter</Label>
          <Text style={{ color: colors.textPrimary, fontSize: font.size["2xl"], fontWeight: "200", marginTop: spacing.sm, lineHeight: 40 }}>
            Not the body you wish for.
          </Text>
          <LinearGradient colors={[colors.accentTeal, colors.accentBlue, colors.accentViolet]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={{ alignSelf: "flex-start", borderRadius: 4, marginTop: 2 }}>
            <Text style={{ color: colors.bg, fontSize: font.size["2xl"], fontWeight: "600", paddingHorizontal: 6 }}>
              The body you can build.
            </Text>
          </LinearGradient>

          <View style={{ marginTop: spacing.xxl, gap: spacing.lg }}>
            {points.map((p) => (
              <View key={p.icon} style={{ flexDirection: "row", gap: spacing.md, alignItems: "flex-start" }}>
                <View style={{ width: 36, height: 36, borderRadius: 10, borderWidth: 1, borderColor: colors.border, alignItems: "center", justifyContent: "center" }}>
                  <Feather name={p.icon} size={18} color={colors.accentTeal} />
                </View>
                <Text style={{ color: colors.textSecondary, fontSize: font.size.base, flex: 1, lineHeight: 22 }}>{p.text}</Text>
              </View>
            ))}
          </View>
        </View>

        <View style={{ gap: spacing.md }}>
          <GradientButton testID="welcome-get-started" label="Create account" icon="arrow-right" onPress={() => router.push("/auth/signup")} />
          <Text testID="welcome-login-link" onPress={() => router.push("/auth/login")} style={{ color: colors.textSecondary, textAlign: "center", fontSize: font.size.base }}>
            I already have an account
          </Text>
        </View>
      </View>
    </Screen>
  );
}

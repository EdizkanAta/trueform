import { useEffect, useState } from "react";
import { Dimensions, Pressable, ScrollView, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Image } from "expo-image";
import { BlurView } from "expo-blur";
import { LinearGradient } from "expo-linear-gradient";
import { Feather } from "@expo/vector-icons";

import { useTheme } from "@/src/theme/ThemeContext";
import { overlay } from "@/src/theme/theme";
import { useAuth } from "@/src/context/AuthContext";
import { api, fileUrl } from "@/src/api/client";
import { GradientButton, Label, Screen, Card, MedicalDisclaimer } from "@/src/components/ui";
import { kgToDisplay } from "@/src/lib/format";

type Render = { path: string; weight_kg: number; weight_lb: number; body_fat_pct: number; what_it_takes: string };
type Targets = {
  base_photo_path: string;
  renders: Record<string, Render>;
  engine: { reasoning: string; exceeds_stretch: boolean; realistic_timeline_weeks: number | null; condition_notes: string[] };
};

const LABELS = ["conservative", "expected", "stretch"] as const;
const TITLES: Record<string, string> = { conservative: "Conservative", expected: "Expected", stretch: "Stretch" };
const SUB: Record<string, string> = { conservative: "80% adherence", expected: "Typical result", stretch: "Near-max safe" };

export default function TargetsScreen() {
  const router = useRouter();
  const { colors, spacing, font, radius } = useTheme();
  const insets = useSafeAreaInsets();
  const { user, refresh } = useAuth();

  const [data, setData] = useState<Targets | null>(null);
  const [selected, setSelected] = useState<string>("expected");
  const [blur, setBlur] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const W = Dimensions.get("window").width;
  const cardW = W - spacing.lg * 2;

  useEffect(() => {
    api.get<Targets>("/targets").then(setData).catch((e) => setErr(e?.detail || "Could not load targets"));
  }, []);

  const choose = async () => {
    setBusy(true);
    try {
      await api.post("/target/choose", { label: selected });
      await refresh();
      router.replace("/(tabs)");
    } catch (e: any) {
      setErr(e?.detail || "Could not build plan");
    } finally {
      setBusy(false);
    }
  };

  if (!data) {
    return (
      <Screen>
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.lg }}>
          <Text style={{ color: colors.textSecondary }}>{err || "Loading your targets…"}</Text>
        </View>
      </Screen>
    );
  }

  const unit = user?.unit_preference || "metric";

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ paddingTop: insets.top + spacing.md, paddingBottom: insets.bottom + 100 }}>
        <View style={{ paddingHorizontal: spacing.lg }}>
          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
            <Label>Your realistic targets</Label>
            <Pressable testID="targets-blur-toggle" onPress={() => setBlur((b) => !b)} style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
              <Feather name={blur ? "eye-off" : "eye"} size={16} color={colors.textSecondary} />
              <Text style={{ color: colors.textSecondary, fontSize: font.size.xs }}>{blur ? "Blurred" : "Blur"}</Text>
            </Pressable>
          </View>
          <Text style={{ color: colors.textPrimary, fontSize: font.size.xl, fontWeight: "200", marginTop: 4 }}>
            Three honest estimates
          </Text>
          <Text style={{ color: colors.textSecondary, fontSize: font.size.sm, marginTop: 4 }}>
            Same you — face, pose, skin, hair, clothing. Only body composition changes.
          </Text>
        </View>

        <ScrollView horizontal pagingEnabled showsHorizontalScrollIndicator={false}
          contentContainerStyle={{ paddingHorizontal: spacing.lg, gap: spacing.md, paddingVertical: spacing.md }}
          snapToInterval={cardW + spacing.md} decelerationRate="fast">
          {LABELS.map((label) => {
            const r = data.renders[label];
            const isSel = selected === label;
            const w = kgToDisplay(r.weight_kg, unit);
            return (
              <Pressable key={label} testID={`target-card-${label}`} onPress={() => setSelected(label)}
                style={{ width: cardW, borderRadius: radius.md, overflow: "hidden", borderWidth: 2, borderColor: isSel ? colors.accentTeal : colors.border }}>
                <View style={{ height: 380, backgroundColor: colors.surface }}>
                  <Image source={{ uri: fileUrl(r.path) }} style={{ width: "100%", height: "100%" }} contentFit="cover" />
                  {blur ? <BlurView intensity={60} tint="dark" style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }} /> : null}
                  <LinearGradient colors={["transparent", colors.scrim, colors.bg]} style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 180 }} />
                  <View style={{ position: "absolute", top: 12, left: 12, backgroundColor: overlay.scrim, paddingHorizontal: 10, paddingVertical: 4, borderRadius: radius.pill }}>
                    <Text style={{ color: overlay.onImage, fontSize: font.size.xs, letterSpacing: 1 }}>ESTIMATE</Text>
                  </View>
                  <View style={{ position: "absolute", left: spacing.md, right: spacing.md, bottom: spacing.md }}>
                    <Text style={{ color: colors.textPrimary, fontSize: font.size.lg, fontWeight: "600" }}>{TITLES[label]}</Text>
                    <Text style={{ color: colors.textSecondary, fontSize: font.size.xs }}>{SUB[label]}</Text>
                    <View style={{ flexDirection: "row", gap: spacing.lg, marginTop: spacing.sm }}>
                      <View>
                        <Text style={{ color: colors.textPrimary, fontSize: font.size.xl, fontWeight: "200" }}>{w.value}<Text style={{ fontSize: font.size.sm }}> {w.unit}</Text></Text>
                        <Text style={{ color: colors.textTertiary, fontSize: font.size.xs, letterSpacing: 1 }}>WEIGHT</Text>
                      </View>
                      <View>
                        <Text style={{ color: colors.textPrimary, fontSize: font.size.xl, fontWeight: "200" }}>{r.body_fat_pct}<Text style={{ fontSize: font.size.sm }}>%</Text></Text>
                        <Text style={{ color: colors.textTertiary, fontSize: font.size.xs, letterSpacing: 1 }}>BODY FAT</Text>
                      </View>
                    </View>
                    <Text style={{ color: colors.textSecondary, fontSize: font.size.xs, marginTop: 6 }}>{r.what_it_takes}</Text>
                  </View>
                  {isSel ? (
                    <View style={{ position: "absolute", top: 12, right: 12, width: 26, height: 26, borderRadius: 13, backgroundColor: colors.accentTeal, alignItems: "center", justifyContent: "center" }}>
                      <Feather name="check" size={16} color={colors.onAccent} />
                    </View>
                  ) : null}
                </View>
              </Pressable>
            );
          })}
        </ScrollView>

        <View style={{ paddingHorizontal: spacing.lg, gap: spacing.md }}>
          <Card testID="engine-reasoning">
            <View style={{ flexDirection: "row", gap: 8, alignItems: "center", marginBottom: 6 }}>
              <Feather name="cpu" size={16} color={colors.accentTeal} />
              <Label>Why these numbers</Label>
            </View>
            <Text style={{ color: colors.textSecondary, fontSize: font.size.sm, lineHeight: 20 }}>{data.engine.reasoning}</Text>
          </Card>

          {data.engine.exceeds_stretch && data.engine.realistic_timeline_weeks ? (
            <Card style={{ borderColor: colors.warning }}>
              <Text style={{ color: colors.warning, fontWeight: "600", marginBottom: 4 }}>Your target is beyond a safe pace</Text>
              <Text style={{ color: colors.textSecondary, fontSize: font.size.sm, lineHeight: 20 }}>
                To reach it safely you'd need about {data.engine.realistic_timeline_weeks} weeks. We've
                capped these estimates at the healthy maximum for your chosen timeline.
              </Text>
            </Card>
          ) : null}

          <MedicalDisclaimer />
        </View>
      </ScrollView>

      <View style={{ position: "absolute", left: spacing.lg, right: spacing.lg, bottom: insets.bottom + spacing.md }}>
        {err ? <Text style={{ color: colors.alert, marginBottom: 8 }}>{err}</Text> : null}
        <GradientButton testID="targets-choose" label={`Choose ${TITLES[selected]} & build plan`} loading={busy} onPress={choose} />
      </View>
    </Screen>
  );
}

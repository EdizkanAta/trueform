import { useEffect, useRef, useState } from "react";
import { ScrollView, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";
import { Feather } from "@expo/vector-icons";

import { useTheme } from "@/src/theme/ThemeContext";
import { overlay } from "@/src/theme/theme";
import { useAuth } from "@/src/context/AuthContext";
import { api, fileUrl } from "@/src/api/client";
import { Label, Screen, Skeleton, MedicalDisclaimer } from "@/src/components/ui";
import { kgToDisplay } from "@/src/lib/format";

type Item = {
  timeline_weeks: number; weight_kg: number; weight_lb: number;
  body_fat_pct: number; what_it_takes: string; path: string;
};
type Optimum = { current_body_fat_pct: number; current_weight_kg: number; direction: string; items: Item[] };

export default function OptimumScreen() {
  const router = useRouter();
  const { colors, spacing, font, radius } = useTheme();
  const insets = useSafeAreaInsets();
  const { user } = useAuth();

  const [data, setData] = useState<Optimum | null>(null);
  const [progress, setProgress] = useState(8);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<any>(null);

  const poll = (jobId: string) => {
    pollRef.current = setInterval(async () => {
      try {
        const j = await api.get<any>(`/optimum/job/${jobId}`);
        setProgress(j.progress || 10);
        if (j.status === "done") {
          clearInterval(pollRef.current);
          setData({
            current_body_fat_pct: j.current_body_fat_pct,
            current_weight_kg: j.current_weight_kg,
            direction: j.direction, items: j.items,
          });
        } else if (j.status === "error") {
          clearInterval(pollRef.current);
          setError(j.error || "Could not build your best case");
        }
      } catch {}
    }, 2500);
  };

  useEffect(() => {
    (async () => {
      try {
        const res = await api.post<{ job_id: string | null; status: string; cached: boolean }>("/optimum");
        if (res.status === "done" || res.cached) {
          const doc = await api.get<Optimum>("/optimum");
          setData(doc);
        } else if (res.job_id) {
          poll(res.job_id);
        }
      } catch (e: any) {
        setError(e?.detail || "Could not start");
      }
    })();
    return () => clearInterval(pollRef.current);
  }, []);

  const unit = user?.unit_preference || "metric";

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ paddingTop: insets.top + spacing.md, paddingBottom: insets.bottom + spacing.xl }}>
        <View style={{ paddingHorizontal: spacing.lg }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: spacing.md }}>
            <Feather name="chevron-left" size={26} color={colors.textPrimary} onPress={() => router.back()} />
            <Label>Your best case</Label>
          </View>
          <Text style={{ color: colors.textPrimary, fontSize: font.size.xl, fontWeight: "200", marginTop: 6 }}>
            What longer commitment buys
          </Text>
          <Text style={{ color: colors.textSecondary, fontSize: font.size.sm, marginTop: 4 }}>
            The engine’s safe maximum for your body across three timelines. Same you — only body
            composition changes.
          </Text>
        </View>

        {!data && !error ? (
          <View style={{ paddingHorizontal: spacing.lg, marginTop: spacing.lg }}>
            <View style={{ height: 6, borderRadius: 3, backgroundColor: colors.surface }}>
              <View style={{ width: `${progress}%`, height: 6, borderRadius: 3, backgroundColor: colors.accentTeal }} />
            </View>
            <Text style={{ color: colors.textSecondary, fontSize: font.size.sm, marginTop: 8 }}>
              Rendering your safe maximum at 16, 26 &amp; 39 weeks · {progress}%
            </Text>
            <View style={{ flexDirection: "row", gap: spacing.md, marginTop: spacing.lg }}>
              {[0, 1, 2].map((i) => (
                <View key={i} style={{ flex: 1, gap: 8 }}>
                  <Skeleton height={200} radius={16} />
                  <Skeleton height={12} width="70%" />
                </View>
              ))}
            </View>
          </View>
        ) : null}

        {error ? (
          <View style={{ paddingHorizontal: spacing.lg, marginTop: spacing.lg }}>
            <Text style={{ color: colors.alert }}>{error}</Text>
          </View>
        ) : null}

        {data ? (
          <>
            <View style={{ paddingHorizontal: spacing.lg, marginTop: spacing.md }}>
              <Text style={{ color: colors.textTertiary, fontSize: font.size.xs }}>
                Today: ~{kgToDisplay(data.current_weight_kg, unit).value} {kgToDisplay(data.current_weight_kg, unit).unit} · {data.current_body_fat_pct}% body fat
              </Text>
            </View>
            {data.items.map((it) => {
              const w = kgToDisplay(it.weight_kg, unit);
              return (
                <View key={it.timeline_weeks} style={{ paddingHorizontal: spacing.lg, marginTop: spacing.md }}>
                  <View style={{ borderRadius: radius.md, overflow: "hidden", borderWidth: 1, borderColor: colors.border }}>
                    <View style={{ height: 300, backgroundColor: colors.surface }}>
                      <Image source={{ uri: fileUrl(it.path) }} style={{ width: "100%", height: "100%" }} contentFit="cover" />
                      <LinearGradient colors={["transparent", colors.scrim, colors.bg]} style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 170 }} />
                      <View style={{ position: "absolute", top: 12, left: 12, backgroundColor: overlay.scrim, paddingHorizontal: 10, paddingVertical: 4, borderRadius: radius.pill }}>
                        <Text style={{ color: overlay.onImage, fontSize: font.size.xs, letterSpacing: 1 }}>ESTIMATE</Text>
                      </View>
                      <View style={{ position: "absolute", top: 12, right: 12, backgroundColor: colors.accentTeal, paddingHorizontal: 10, paddingVertical: 4, borderRadius: radius.pill }}>
                        <Text style={{ color: colors.onAccent, fontSize: font.size.xs, fontWeight: "700" }}>{it.timeline_weeks} WEEKS</Text>
                      </View>
                      <View style={{ position: "absolute", left: spacing.md, right: spacing.md, bottom: spacing.md, flexDirection: "row", gap: spacing.lg }}>
                        <View>
                          <Text style={{ color: colors.textPrimary, fontSize: font.size.xl, fontWeight: "200" }}>{w.value}<Text style={{ fontSize: font.size.sm }}> {w.unit}</Text></Text>
                          <Text style={{ color: colors.textTertiary, fontSize: font.size.xs, letterSpacing: 1 }}>WEIGHT</Text>
                        </View>
                        <View>
                          <Text style={{ color: colors.textPrimary, fontSize: font.size.xl, fontWeight: "200" }}>{it.body_fat_pct}<Text style={{ fontSize: font.size.sm }}>%</Text></Text>
                          <Text style={{ color: colors.textTertiary, fontSize: font.size.xs, letterSpacing: 1 }}>BODY FAT</Text>
                        </View>
                      </View>
                    </View>
                  </View>
                  <Text style={{ color: colors.textSecondary, fontSize: font.size.xs, marginTop: 6 }}>{it.what_it_takes}</Text>
                </View>
              );
            })}
            <View style={{ paddingHorizontal: spacing.lg, marginTop: spacing.lg }}>
              <MedicalDisclaimer />
            </View>
          </>
        ) : null}
      </ScrollView>
    </Screen>
  );
}

import { useEffect, useRef, useState } from "react";
import { Text, View, ScrollView } from "react-native";
import { useRouter, useLocalSearchParams } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAuth } from "@/src/context/AuthContext";
import { api } from "@/src/api/client";
import { GradientButton, OutlineButton, Label, Screen, Skeleton, Card } from "@/src/components/ui";

type Blocked = { blocked: boolean; reasons: string[]; message: string; resources: { name: string; contact: string }[] };

export default function Generating() {
  const router = useRouter();
  const { colors, spacing, font } = useTheme();
  const insets = useSafeAreaInsets();
  const { refresh, user } = useAuth();
  const { job } = useLocalSearchParams<{ job?: string }>();

  const [progress, setProgress] = useState(5);
  const [status, setStatus] = useState<"running" | "error" | "done">("running");
  const [error, setError] = useState<string | null>(null);
  const [blocked, setBlocked] = useState<Blocked | null>(null);
  const pollRef = useRef<any>(null);

  const start = async () => {
    setStatus("running"); setError(null); setBlocked(null); setProgress(5);
    // Goal edit / regeneration: a job was already started by the backend.
    if (job) { poll(job); return; }
    // If targets already exist, skip straight through.
    if (user?.has_targets) { router.replace("/targets"); return; }
    try {
      const res = await api.post<{ job_id: string }>("/generate");
      poll(res.job_id);
    } catch (e: any) {
      if (e?.status === 403 && e?.detail?.blocked) {
        setBlocked(e.detail as Blocked);
      } else {
        setStatus("error");
        setError(e?.detail || e?.message || "Could not start generation");
      }
    }
  };

  const poll = (jobId: string) => {
    pollRef.current = setInterval(async () => {
      try {
        const j = await api.get<{ status: string; progress: number; error?: string }>(`/generate/${jobId}`);
        setProgress(j.progress);
        if (j.status === "done") {
          clearInterval(pollRef.current);
          setStatus("done");
          await refresh();
          router.replace("/targets");
        } else if (j.status === "error") {
          clearInterval(pollRef.current);
          setStatus("error");
          setError(j.error || "Generation failed");
        }
      } catch {
        // keep polling through transient errors
      }
    }, 2500);
  };

  useEffect(() => {
    start();
    return () => clearInterval(pollRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (blocked) {
    return (
      <Screen>
        <ScrollView contentContainerStyle={{ paddingTop: insets.top + spacing.xl, paddingHorizontal: spacing.lg, paddingBottom: insets.bottom + spacing.lg, gap: spacing.md }}>
          <Feather name="heart" size={32} color={colors.accentTeal} />
          <Text style={{ color: colors.textPrimary, fontSize: font.size.xl, fontWeight: "200" }}>We're pausing here — for you</Text>
          <Text style={{ color: colors.textSecondary, lineHeight: 22 }}>{blocked.message}</Text>
          <Text style={{ color: colors.textSecondary, lineHeight: 22 }}>
            TrueForm isn't the right tool during pregnancy or with a history of an eating disorder.
            Please work directly with a professional who can support you safely.
          </Text>
          {blocked.resources.map((r) => (
            <Card key={r.name}>
              <Text style={{ color: colors.textPrimary, fontWeight: "600" }}>{r.name}</Text>
              <Text style={{ color: colors.accentTeal, marginTop: 4 }}>{r.contact}</Text>
            </Card>
          ))}
          <OutlineButton testID="blocked-back" label="Back to profile" onPress={() => router.replace("/(tabs)/profile")} />
        </ScrollView>
      </Screen>
    );
  }

  return (
    <Screen>
      <View style={{ flex: 1, paddingTop: insets.top + spacing.xl, paddingHorizontal: spacing.lg, paddingBottom: insets.bottom + spacing.md }}>
        <Label>Building your target matrix</Label>
        <Text style={{ color: colors.textPrimary, fontSize: font.size.xl, fontWeight: "200", marginTop: 6 }}>
          {status === "error" ? "Something interrupted the render" : "Analyzing your inputs…"}
        </Text>

        {status !== "error" && (
          <>
            <View style={{ height: 6, borderRadius: 3, backgroundColor: colors.surface, marginTop: spacing.lg }}>
              <View style={{ width: `${progress}%`, height: 6, borderRadius: 3, backgroundColor: colors.accentTeal }} />
            </View>
            <Text style={{ color: colors.textSecondary, fontSize: font.size.sm, marginTop: 8 }}>
              {progress < 20 ? "Computing safe rates & body-composition estimates"
                : progress < 95 ? "Rendering conservative · expected · stretch"
                : "Finalizing"} · {progress}%
            </Text>

            <View style={{ flexDirection: "row", gap: spacing.md, marginTop: spacing.xl }}>
              {[0, 1, 2].map((i) => (
                <View key={i} style={{ flex: 1, gap: 8 }}>
                  <Skeleton height={200} radius={16} />
                  <Skeleton height={12} width="70%" />
                  <Skeleton height={10} width="50%" />
                </View>
              ))}
            </View>
            <View style={{ marginTop: spacing.xl, gap: 10 }}>
              <Skeleton height={14} width="90%" />
              <Skeleton height={14} width="80%" />
              <Skeleton height={14} width="60%" />
            </View>
          </>
        )}

        {status === "error" && (
          <View style={{ marginTop: spacing.lg, gap: spacing.md }}>
            <Text testID="generating-error" style={{ color: colors.textSecondary, lineHeight: 20 }}>
              {error}. Your photo and inputs are saved — you can retry now.
            </Text>
            <GradientButton testID="generating-retry" label="Retry render" icon="refresh-cw" onPress={() => { pollRef.current && clearInterval(pollRef.current); (async () => { setStatus("running"); setError(null); setProgress(5); try { const res = await api.post<{ job_id: string }>("/generate"); poll(res.job_id); } catch (e: any) { setStatus("error"); setError(e?.detail || e?.message || "Could not start generation"); } })(); }} />
          </View>
        )}
      </View>
    </Screen>
  );
}

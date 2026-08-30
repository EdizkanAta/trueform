import { useCallback, useState } from "react";
import { ScrollView, Text, View, RefreshControl } from "react-native";
import { useFocusEffect, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAuth } from "@/src/context/AuthContext";
import { api } from "@/src/api/client";
import {
  Card, CheckBox, Label, ListRow, Screen, Skeleton, StatReadout, MedicalDisclaimer,
} from "@/src/components/ui";

type Meal = { slug: string; name: string; meal_type: string; kcal: number };
type Ex = { slug: string; name: string; sets: number; reps: string };
type Today = {
  date: string; weekday: string;
  day_plan: { focus: string; type: string; workout: Ex[]; meals: Meal[] } | null;
  log: any; streak: number; next_milestone: { week: number; weeks_away: number } | null;
  has_plan: boolean;
};

export default function TodayScreen() {
  const router = useRouter();
  const { colors, spacing, font } = useTheme();
  const insets = useSafeAreaInsets();
  const { user } = useAuth();

  const [data, setData] = useState<Today | null>(null);
  const [meals, setMeals] = useState<string[]>([]);
  const [workout, setWorkout] = useState(false);
  const [energy, setEnergy] = useState<number | null>(null);
  const [pain, setPain] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [recovery, setRecovery] = useState<any[] | null>(null);

  const load = useCallback(async () => {
    const d = await api.get<Today>("/today");
    setData(d);
    setMeals(d.log?.meals_completed || []);
    setWorkout(!!d.log?.workout_completed);
    setEnergy(d.log?.energy ?? null);
    setPain(d.log?.pain ?? null);
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const save = async (patch: Partial<any>) => {
    const body = {
      date: data?.date, meals_completed: meals, workout_completed: workout,
      energy, pain, ...patch,
    };
    const res = await api.post<{ recovery_triggered: boolean; recovery_protocol?: any[] }>("/logs", body);
    if (res.recovery_triggered && res.recovery_protocol) setRecovery(res.recovery_protocol);
    else setRecovery(null);
  };

  const toggleMeal = (slug: string) => {
    const next = meals.includes(slug) ? meals.filter((m) => m !== slug) : [...meals, slug];
    setMeals(next); save({ meals_completed: next });
  };
  const toggleWorkout = () => { const n = !workout; setWorkout(n); save({ workout_completed: n }); };

  if (!data) {
    return (
      <Screen>
        <ScrollView contentContainerStyle={{ paddingTop: insets.top + spacing.lg, paddingHorizontal: spacing.lg, gap: spacing.md }}>
          <Skeleton height={60} /><Skeleton height={120} /><Skeleton height={200} />
        </ScrollView>
      </Screen>
    );
  }

  const dp = data.day_plan;

  return (
    <Screen>
      <ScrollView
        contentContainerStyle={{ paddingTop: insets.top + spacing.md, paddingHorizontal: spacing.lg, paddingBottom: spacing.xl }}
        refreshControl={<RefreshControl refreshing={refreshing} tintColor={colors.accentTeal} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} />}
      >
        <Label>{data.weekday}</Label>
        <Text style={{ color: colors.textPrimary, fontSize: font.size.xl, fontWeight: "200", marginTop: 2 }}>Today</Text>

        <View style={{ flexDirection: "row", gap: spacing.md, marginTop: spacing.lg }}>
          <Card style={{ flex: 1 }}><StatReadout value={data.streak} label="day streak" size={font.size["2xl"]} /></Card>
          <Card style={{ flex: 1 }}>
            <StatReadout value={data.next_milestone ? `W${data.next_milestone.week}` : "—"} label="next milestone" size={font.size["2xl"]} />
            {data.next_milestone ? <Text style={{ color: colors.textTertiary, fontSize: font.size.xs, marginTop: 2 }}>{data.next_milestone.weeks_away} weeks away</Text> : null}
          </Card>
        </View>

        {!data.has_plan ? (
          <Card style={{ marginTop: spacing.md }}>
            <Text style={{ color: colors.textSecondary }}>No plan yet. Finish choosing your target to unlock today.</Text>
          </Card>
        ) : (
          <>
            {/* Workout */}
            <View style={{ marginTop: spacing.lg }}>
              <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: spacing.sm }}>
                <Label>Today's workout · {dp?.focus}</Label>
                {dp?.type === "workout" ? (
                  <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                    <Text style={{ color: colors.textSecondary, fontSize: font.size.xs }}>Done</Text>
                    <CheckBox testID="today-workout-check" checked={workout} onToggle={toggleWorkout} />
                  </View>
                ) : null}
              </View>
              <Card>
                {dp?.type === "recovery" ? (
                  <Text style={{ color: colors.textSecondary }}>Recovery day — stretch, walk, hydrate, sleep.</Text>
                ) : (
                  (dp?.workout || []).map((ex, i) => (
                    <ListRow key={ex.slug + i} title={ex.name} subtitle={`${ex.sets} × ${ex.reps}`} />
                  ))
                )}
              </Card>
            </View>

            {/* Meals */}
            <View style={{ marginTop: spacing.lg }}>
              <Label>Nutrition · check off as you eat</Label>
              <Card style={{ marginTop: spacing.sm }}>
                {(dp?.meals || []).map((m) => (
                  <ListRow
                    key={m.slug}
                    title={m.name}
                    subtitle={`${m.meal_type} · ${m.kcal} kcal`}
                    right={<CheckBox testID={`today-meal-${m.slug}`} checked={meals.includes(m.slug)} onToggle={() => toggleMeal(m.slug)} />}
                  />
                ))}
              </Card>
            </View>
          </>
        )}

        {/* Quick log */}
        <View style={{ marginTop: spacing.lg }}>
          <Label>Quick log</Label>
          <Card style={{ marginTop: spacing.sm, gap: spacing.md }}>
            <ScaleRow testID="today-energy" label="Energy" value={energy} onChange={(v) => { setEnergy(v); save({ energy: v }); }} />
            <ScaleRow testID="today-pain" label="Pain" value={pain} onChange={(v) => { setPain(v); save({ pain: v }); }} />
            <Text style={{ color: colors.textTertiary, fontSize: font.size.xs }}>Log weight in Progress →</Text>
          </Card>
        </View>

        {recovery ? (
          <Card testID="today-recovery" style={{ marginTop: spacing.md, borderColor: colors.accentTeal }}>
            <View style={{ flexDirection: "row", gap: 8, alignItems: "center", marginBottom: 6 }}>
              <Feather name="shield" size={16} color={colors.accentTeal} />
              <Label>Recovery protocol</Label>
            </View>
            {recovery.map((r) => (
              <Text key={r.title} style={{ color: colors.textSecondary, fontSize: font.size.sm, marginTop: 4 }}>• {r.title}: {r.detail}</Text>
            ))}
          </Card>
        ) : null}

        {/* Coach nudge */}
        <Card testID="today-coach-nudge" style={{ marginTop: spacing.md }}>
          <View style={{ flexDirection: "row", gap: spacing.md, alignItems: "center" }}>
            <Feather name="message-circle" size={20} color={colors.accentTeal} />
            <Text style={{ color: colors.textSecondary, flex: 1, fontSize: font.size.sm }}>
              Skipped a meal or feeling off? Tell your coach — we'll adjust, not judge.
            </Text>
            <Feather name="chevron-right" size={20} color={colors.textTertiary} onPress={() => router.push("/(tabs)/coach")} />
          </View>
        </Card>

        <View style={{ marginTop: spacing.md }}><MedicalDisclaimer /></View>
      </ScrollView>
    </Screen>
  );
}

function ScaleRow({ label, value, onChange, testID }: { label: string; value: number | null; onChange: (v: number) => void; testID?: string }) {
  const { colors, font } = useTheme();
  return (
    <View testID={testID}>
      <Text style={{ color: colors.textSecondary, fontSize: font.size.sm, marginBottom: 6 }}>{label} (1–5)</Text>
      <View style={{ flexDirection: "row", gap: 8 }}>
        {[1, 2, 3, 4, 5].map((n) => {
          const on = value === n;
          return (
            <Text key={n} testID={`${testID}-${n}`} onPress={() => onChange(n)}
              style={{
                width: 44, height: 40, textAlign: "center", lineHeight: 40, borderRadius: 8,
                borderWidth: 1, borderColor: on ? colors.accentTeal : colors.border,
                backgroundColor: on ? colors.accentTeal : "transparent",
                color: on ? colors.onAccent : colors.textSecondary, fontWeight: "600",
              }}>
              {n}
            </Text>
          );
        })}
      </View>
    </View>
  );
}

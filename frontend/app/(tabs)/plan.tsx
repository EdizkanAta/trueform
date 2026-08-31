import { useCallback, useState } from "react";
import { Modal, Pressable, ScrollView, Text, View } from "react-native";
import { useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";

import { useTheme } from "@/src/theme/ThemeContext";
import { overlay } from "@/src/theme/theme";
import { api, fileUrl, mediaUrl } from "@/src/api/client";
import { Card, Chip, Label, ListRow, Screen, Skeleton, StatReadout, MedicalDisclaimer } from "@/src/components/ui";
import { FullBleedCard } from "@/src/components/FullBleedCard";
import { ENV_LABELS } from "@/src/lib/format";

const MEAL_IMG = "https://images.unsplash.com/photo-1547592180-85f173990554?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA3MDR8MHwxfHNlYXJjaHwxfHxoZWFsdGh5JTIwbWVhbCUyMHByZXAlMjBmb29kJTIwbmV1dHJhbCUyMGJhY2tncm91bmR8ZW58MHx8fHwxNzg4MTI2NTEyfDA&ixlib=rb-4.1.0&q=85";
const GYM_IMG = "https://images.unsplash.com/photo-1576678927484-cc907957088c?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxODl8MHwxfHNlYXJjaHwxfHxneW0lMjBlcXVpcG1lbnQlMjBkdW1iYmVsbHMlMjBkYXJrJTIwbmV1dHJhbCUyMGJhY2tncm91bmR8ZW58MHx8fHwxNzg4MTI2NTEyfDA&ixlib=rb-4.1.0&q=85";

const DAY_ABBR: Record<string, string> = { Monday: "Mon", Tuesday: "Tue", Wednesday: "Wed", Thursday: "Thu", Friday: "Fri", Saturday: "Sat", Sunday: "Sun" };
const ENVS = ["gym", "home_equipment", "home_no_equipment"];

export default function PlanScreen() {
  const { colors, spacing, font, radius } = useTheme();
  const insets = useSafeAreaInsets();
  const [plan, setPlan] = useState<any>(null);
  const [dayIdx, setDayIdx] = useState(0);
  const [envOverride, setEnvOverride] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [blurMedia, setBlurMedia] = useState(true);
  const [selEx, setSelEx] = useState<any>(null);

  const load = useCallback(async (env?: string | null) => {
    const q = env ? `?environment=${env}` : "";
    const p = await api.get<any>(`/plan${q}`);
    setPlan(p);
  }, []);

  useFocusEffect(useCallback(() => { load(envOverride); }, [load, envOverride]));

  if (!plan) {
    return (
      <Screen>
        <ScrollView contentContainerStyle={{ paddingTop: insets.top + spacing.lg, paddingHorizontal: spacing.lg, gap: spacing.md }}>
          <Skeleton height={40} /><Skeleton height={56} /><Skeleton height={160} /><Skeleton height={160} />
        </ScrollView>
      </Screen>
    );
  }

  const day = plan.days[dayIdx];
  const currentEnv = envOverride || day?.environment;
  const chosenRenderUri = fileUrl(plan.chosen_render_path);

  return (
    <Screen>
      {/* Sticky header */}
      <View style={{ paddingTop: insets.top + spacing.md, paddingHorizontal: spacing.lg, borderBottomWidth: 1, borderBottomColor: colors.border, paddingBottom: spacing.sm }}>
        <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-end" }}>
          <View>
            <Label>Your plan · {plan.chosen_target}</Label>
            <Text style={{ color: colors.textPrimary, fontSize: font.size.xl, fontWeight: "200" }}>{day.focus}</Text>
          </View>
          <StatReadout value={plan.daily_kcal} unit="kcal" label="daily target" align="center" size={font.size["2xl"]} />
        </View>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: spacing.sm, paddingVertical: spacing.sm }}>
          {plan.days.map((d: any, i: number) => (
            <Chip key={d.day} testID={`plan-day-${d.day}`} label={DAY_ABBR[d.day]} active={i === dayIdx} onPress={() => setDayIdx(i)} />
          ))}
        </ScrollView>

        <View style={{ flexDirection: "row", alignItems: "center", gap: spacing.sm }}>
          <Text style={{ color: colors.textTertiary, fontSize: font.size.xs }}>Setting:</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: spacing.sm }}>
            {ENVS.map((e) => (
              <Chip key={e} testID={`plan-env-${e}`} label={ENV_LABELS[e]} active={currentEnv === e} onPress={() => setEnvOverride(e)} />
            ))}
          </ScrollView>
        </View>
        {envOverride ? (
          <Text style={{ color: colors.textTertiary, fontSize: font.size.xs, marginTop: 4 }}>
            Showing a {ENV_LABELS[envOverride]} version (e.g. traveling). Tap your scheduled setting to reset.
          </Text>
        ) : null}
      </View>

      <ScrollView contentContainerStyle={{ paddingHorizontal: spacing.lg, paddingTop: spacing.md, paddingBottom: spacing.xl }}>
        {/* Workout */}
        <View style={{ height: 150, borderRadius: radius.md, overflow: "hidden", backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border }}>
          <Image source={{ uri: chosenRenderUri || GYM_IMG }} style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }} contentFit="cover" blurRadius={chosenRenderUri && blurMedia ? 65 : 0} />
          <LinearGradient colors={["transparent", colors.scrim, colors.bg]} style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 110 }} />
          {chosenRenderUri ? (
            <Pressable testID="plan-blur-toggle" onPress={() => setBlurMedia((b) => !b)} style={{ position: "absolute", top: 10, right: 10, backgroundColor: overlay.scrim, borderRadius: radius.pill, paddingHorizontal: 10, paddingVertical: 6, flexDirection: "row", gap: 6, alignItems: "center" }}>
              <Feather name={blurMedia ? "eye-off" : "eye"} size={14} color={overlay.onImage} />
              <Text style={{ color: overlay.onImage, fontSize: font.size.xs }}>{blurMedia ? "Blurred" : "Blur"}</Text>
            </Pressable>
          ) : null}
          <View style={{ position: "absolute", left: spacing.md, bottom: spacing.md }}>
            <Text style={{ color: colors.textPrimary, fontSize: font.size.lg, fontWeight: "600" }}>{day.type === "recovery" ? "Recovery Day" : `Workout · ${day.focus}`}</Text>
            <Text style={{ color: colors.textSecondary, fontSize: font.size.sm }}>{ENV_LABELS[currentEnv] || currentEnv}</Text>
          </View>
        </View>
        <Card style={{ marginTop: spacing.sm }}>
          {day.type === "recovery" ? (
            (plan.recovery_protocol || []).map((r: any) => (
              <ListRow key={r.title} icon="wind" title={r.title} subtitle={r.detail} />
            ))
          ) : (
            day.workout.map((ex: any, i: number) => (
              <Pressable key={ex.slug + i} testID={`plan-ex-${ex.slug}`} onPress={() => setSelEx(ex)} style={{ flexDirection: "row", alignItems: "center", gap: 12, paddingVertical: spacing.sm, borderBottomWidth: i < day.workout.length - 1 ? 1 : 0, borderBottomColor: colors.border }}>
                {ex.media?.demo_url || ex.poster_image_url ? (
                  <Image source={{ uri: mediaUrl(ex.poster_image_url || ex.media?.demo_url) }} style={{ width: 52, height: 52, borderRadius: radius.sm, backgroundColor: colors.surfaceElevated }} contentFit="cover" />
                ) : (
                  <View style={{ width: 52, height: 52, borderRadius: radius.sm, backgroundColor: colors.surfaceElevated, alignItems: "center", justifyContent: "center" }}>
                    <Feather name="activity" size={20} color={colors.textTertiary} />
                  </View>
                )}
                <View style={{ flex: 1 }}>
                  <Text style={{ color: colors.textPrimary, fontSize: font.size.md, fontWeight: "500" }}>{ex.name}</Text>
                  <Text style={{ color: colors.textSecondary, fontSize: font.size.sm }}>{ex.sets} × {ex.reps} · rest {ex.rest_sec}s</Text>
                  {ex.safety_note ? <Text style={{ color: colors.warning, fontSize: font.size.xs, marginTop: 2 }}>{ex.safety_note}</Text> : null}
                </View>
                <Feather name="chevron-right" size={20} color={colors.textTertiary} />
              </Pressable>
            ))
          )}
        </Card>

        {/* Meals */}
        <View style={{ marginTop: spacing.lg, gap: spacing.sm }}>
          <Label>Nutrition · {day.meals.length} items · {plan.macros.protein_g}P / {plan.macros.carbs_g}C / {plan.macros.fat_g}F</Label>
          {day.meals.map((m: any) => (
            <View key={m.slug}>
              <FullBleedCard testID={`plan-meal-${m.slug}`} imageUri={MEAL_IMG} title={m.name} subtitle={`${m.meal_type} · ${m.kcal} kcal`} height={130} onPress={() => setExpanded(expanded === m.slug ? null : m.slug)}>
                <View style={{ flexDirection: "row", gap: 6, marginBottom: 6 }}>
                  {(m.tags || []).slice(0, 3).map((t: string) => (
                    <View key={t} style={{ backgroundColor: overlay.scrim, paddingHorizontal: spacing.sm, paddingVertical: 2, borderRadius: radius.pill }}>
                      <Text style={{ color: overlay.onImage, fontSize: 10 }}>{t}</Text>
                    </View>
                  ))}
                </View>
              </FullBleedCard>
              {expanded === m.slug ? (
                <Card style={{ marginTop: 6 }}>
                  <Label>Ingredients</Label>
                  {m.ingredients.map((ing: string, i: number) => <Text key={i} style={{ color: colors.textSecondary, fontSize: font.size.sm, marginTop: 3 }}>• {ing}</Text>)}
                  <View style={{ height: spacing.sm }} />
                  <Label>Method</Label>
                  {m.steps.map((s: string, i: number) => <Text key={i} style={{ color: colors.textSecondary, fontSize: font.size.sm, marginTop: 3 }}>{i + 1}. {s}</Text>)}
                </Card>
              ) : null}
            </View>
          ))}
        </View>

        {/* Lifestyle */}
        <View style={{ marginTop: spacing.lg }}>
          <Label>Lifestyle habits</Label>
          <Card style={{ marginTop: spacing.sm }}>
            {plan.lifestyle_habits.map((h: string, i: number) => (
              <Text key={i} style={{ color: colors.textSecondary, fontSize: font.size.sm, marginVertical: 3 }}>• {h}</Text>
            ))}
          </Card>
        </View>

        <View style={{ marginTop: spacing.md }}><MedicalDisclaimer /></View>
      </ScrollView>

      <Modal visible={!!selEx} transparent animationType="slide" onRequestClose={() => setSelEx(null)}>
        <Pressable style={{ flex: 1, backgroundColor: overlay.scrim, justifyContent: "flex-end" }} onPress={() => setSelEx(null)}>
          <Pressable onPress={() => {}} style={{ backgroundColor: colors.surface, borderTopLeftRadius: radius.lg, borderTopRightRadius: radius.lg, padding: spacing.lg, paddingBottom: insets.bottom + spacing.lg, borderWidth: 1, borderColor: colors.border }}>
            {selEx ? (
              <View>
                <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                  <Text style={{ color: colors.textPrimary, fontSize: font.size.xl, fontWeight: "600", flex: 1 }}>{selEx.name}</Text>
                  <Feather name="x" size={24} color={colors.textSecondary} onPress={() => setSelEx(null)} />
                </View>
                {selEx.poster_image_url || selEx.media?.demo_url ? (
                  <Image source={{ uri: mediaUrl(selEx.poster_image_url || selEx.media?.demo_url) }} style={{ width: "100%", height: 200, borderRadius: radius.md, marginTop: spacing.md, backgroundColor: colors.surfaceElevated }} contentFit="cover" />
                ) : (
                  <View testID="plan-ex-poster-placeholder" style={{ height: 160, borderRadius: radius.md, marginTop: spacing.md, backgroundColor: colors.surfaceElevated, alignItems: "center", justifyContent: "center" }}>
                    <Feather name="activity" size={30} color={colors.textTertiary} />
                    <Text style={{ color: colors.textTertiary, fontSize: font.size.xs, marginTop: 6 }}>Demo coming soon</Text>
                  </View>
                )}
                <View style={{ flexDirection: "row", gap: spacing.xl, marginTop: spacing.md }}>
                  <StatReadout value={selEx.sets} label="sets" size={font.size.xl} />
                  <StatReadout value={selEx.reps} label="reps" size={font.size.lg} />
                  <StatReadout value={`${selEx.rest_sec}s`} label="rest" size={font.size.xl} />
                </View>
                {selEx.safety_note ? <Text style={{ color: colors.warning, fontSize: font.size.sm, marginTop: spacing.sm }}>{selEx.safety_note}</Text> : null}
                <View style={{ marginTop: spacing.md }}>
                  <Label>Form cues</Label>
                  {(selEx.form_cues || []).map((c: string, i: number) => (
                    <Text key={i} style={{ color: colors.textSecondary, fontSize: font.size.sm, marginTop: 4 }}>• {c}</Text>
                  ))}
                </View>
                <Text style={{ color: colors.textTertiary, fontSize: font.size.xs, marginTop: spacing.md }}>Media: {selEx.media?.attribution || "your own library"}</Text>
              </View>
            ) : null}
          </Pressable>
        </Pressable>
      </Modal>
    </Screen>
  );
}

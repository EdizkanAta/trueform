import { useEffect, useState } from "react";
import { Text, View } from "react-native";
import { useRouter } from "expo-router";
import Slider from "@react-native-community/slider";
import { Feather } from "@expo/vector-icons";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAuth } from "@/src/context/AuthContext";
import { api } from "@/src/api/client";
import { Card, Label, GradientButton, OutlineButton, StatReadout } from "@/src/components/ui";
import { OptionGroup, TextField } from "@/src/components/form";
import { kgToDisplay } from "@/src/lib/format";

type Goal = {
  direction: string; desired_weight_kg: number | null; timeline_weeks: number;
};
type GoalResp = { goal: Goal; chosen_target: string | null; has_targets: boolean; has_plan: boolean; archived_goals: number };

const DIR_LABEL: Record<string, string> = { lose: "Lose fat", gain: "Gain muscle", recomp: "Recomp" };
const TARGETS = [
  { value: "conservative", label: "Conservative" },
  { value: "expected", label: "Expected" },
  { value: "stretch", label: "Stretch" },
];

export function MyGoalSection() {
  const router = useRouter();
  const { colors, spacing, font } = useTheme();
  const { user, refresh } = useAuth();

  const [resp, setResp] = useState<GoalResp | null>(null);
  const [editing, setEditing] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);

  const [direction, setDirection] = useState<"lose" | "gain" | "recomp">("lose");
  const [timeline, setTimeline] = useState(16);
  const [goalMode, setGoalMode] = useState<"auto" | "custom">("auto");
  const [desired, setDesired] = useState("");

  const load = async () => {
    try {
      const r = await api.get<GoalResp>("/goal");
      setResp(r);
      setDirection(r.goal.direction as any);
      setTimeline(r.goal.timeline_weeks || 16);
      setGoalMode(r.goal.desired_weight_kg ? "custom" : "auto");
      setDesired(r.goal.desired_weight_kg ? String(r.goal.desired_weight_kg) : "");
    } catch {}
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const switchTarget = async (label: string) => {
    if (!resp || label === resp.chosen_target) return;
    setBusy(true);
    try {
      await api.post("/target/choose", { label });
      await refresh();
      await load();
    } finally { setBusy(false); }
  };

  const saveGoal = async () => {
    setBusy(true);
    try {
      const res = await api.patch<{ job_id: string }>("/goal", {
        direction,
        timeline_weeks: timeline,
        clear_desired_weight: direction === "recomp" || goalMode === "auto",
        desired_weight_kg: (direction !== "recomp" && goalMode === "custom" && desired) ? Number(desired) : null,
      });
      await refresh();
      setEditing(false); setConfirm(false);
      router.push(`/generating?job=${res.job_id}`);
    } finally { setBusy(false); }
  };

  if (!resp) return null;
  const unit = user?.unit_preference || "metric";
  const g = resp.goal;

  return (
    <View style={{ marginTop: spacing.lg }}>
      <Label>My Goal</Label>
      <Card testID="mygoal-card" style={{ marginTop: spacing.sm, gap: spacing.md }}>
        {!editing ? (
          <>
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
              <View>
                <Text style={{ color: colors.textPrimary, fontSize: font.size.lg, fontWeight: "600" }}>
                  {DIR_LABEL[g.direction] || g.direction}
                </Text>
                <Text style={{ color: colors.textSecondary, fontSize: font.size.sm, marginTop: 2 }}>
                  {g.timeline_weeks} weeks
                  {g.desired_weight_kg ? ` · goal ${kgToDisplay(g.desired_weight_kg, unit).value} ${kgToDisplay(g.desired_weight_kg, unit).unit}` : " · showing what's possible"}
                </Text>
              </View>
              <Feather name="edit-2" size={18} color={colors.accentTeal} onPress={() => setEditing(true)} testID="mygoal-edit" />
            </View>

            <View style={{ gap: spacing.sm }}>
              <Label>Active target</Label>
              <OptionGroup testIDPrefix="mygoal-target" value={resp.chosen_target || "expected"}
                onChange={switchTarget} options={TARGETS as any} />
              <Text style={{ color: colors.textTertiary, fontSize: font.size.xs }}>
                Switch anytime — your plan adjusts to the target you pick.
              </Text>
            </View>

            <OutlineButton testID="mygoal-optimum" label="What's my best case?" onPress={() => router.push("/optimum")} />
            {resp.archived_goals > 0 ? (
              <Text style={{ color: colors.textTertiary, fontSize: font.size.xs }}>
                {resp.archived_goals} past goal{resp.archived_goals > 1 ? "s" : ""} archived — old renders & plans are kept.
              </Text>
            ) : null}
          </>
        ) : (
          <>
            <OptionGroup label="Goal direction" testIDPrefix="mygoal-direction" value={direction}
              onChange={(v: any) => setDirection(v)}
              options={[{ value: "lose", label: "Lose fat" }, { value: "gain", label: "Gain muscle" }, { value: "recomp", label: "Recomp" }]} />

            {direction !== "recomp" && (
              <View style={{ gap: spacing.sm }}>
                <OptionGroup label="Target weight" testIDPrefix="mygoal-goalmode" value={goalMode}
                  onChange={(v: any) => setGoalMode(v)}
                  options={[{ value: "auto", label: "Show me what's possible" }, { value: "custom", label: "I have a target" }]} />
                {goalMode === "custom" ? (
                  <TextField testID="mygoal-desired" label="Desired weight (kg)" value={desired} onChangeText={setDesired} placeholder="e.g. 74" keyboardType="numeric" />
                ) : null}
              </View>
            )}

            <View>
              <Label>Timeline</Label>
              <View style={{ marginTop: spacing.sm, marginBottom: spacing.xs }}>
                <StatReadout value={timeline} unit="weeks" label="target horizon" />
              </View>
              <Slider testID="mygoal-timeline" minimumValue={8} maximumValue={52} step={1} value={timeline}
                onValueChange={(v) => setTimeline(Math.round(v))}
                minimumTrackTintColor={colors.accentTeal} maximumTrackTintColor={colors.border} thumbTintColor={colors.accentBlue} />
            </View>

            {!confirm ? (
              <View style={{ gap: spacing.sm }}>
                <GradientButton testID="mygoal-save" label="Save changes" onPress={() => setConfirm(true)} />
                <OutlineButton testID="mygoal-cancel" label="Cancel" onPress={() => { setEditing(false); setConfirm(false); load(); }} />
              </View>
            ) : (
              <View style={{ gap: spacing.sm }}>
                <Text style={{ color: colors.warning, fontSize: font.size.sm, lineHeight: 20 }}>
                  This regenerates your future-self renders and rebuilds your plan. Your current
                  goal, renders and plan are archived (not deleted).
                </Text>
                <GradientButton testID="mygoal-confirm" label={busy ? "Regenerating…" : "Regenerate my plan"} loading={busy} onPress={saveGoal} />
                <OutlineButton testID="mygoal-confirm-cancel" label="Keep current goal" onPress={() => setConfirm(false)} />
              </View>
            )}
          </>
        )}
      </Card>
    </View>
  );
}

import { useState } from "react";
import { Text, View } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import Slider from "@react-native-community/slider";
import { Feather } from "@expo/vector-icons";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAuth } from "@/src/context/AuthContext";
import { api } from "@/src/api/client";
import { GradientButton, Label, Screen, StatReadout } from "@/src/components/ui";
import { TextField, OptionGroup } from "@/src/components/form";
import { CONDITION_LABELS, ENV_LABELS } from "@/src/lib/format";

const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const EQUIPMENT = ["dumbbells", "bands", "bench", "pull-up bar", "kettlebell", "treadmill/bike"];

export default function Onboarding() {
  const router = useRouter();
  const { colors, spacing, font } = useTheme();
  const insets = useSafeAreaInsets();
  const { refresh } = useAuth();

  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);

  const [weight, setWeight] = useState("");
  const [frame, setFrame] = useState<"small" | "medium" | "large">("medium");
  const [activity, setActivity] = useState("moderate");
  const [env, setEnv] = useState<"gym" | "home_equipment" | "home_no_equipment">("gym");
  const [equipment, setEquipment] = useState<string[]>([]);
  const [samePlace, setSamePlace] = useState(true);
  const [schedule, setSchedule] = useState<Record<string, string>>({});
  const [injuries, setInjuries] = useState("");
  const [conditions, setConditions] = useState<string[]>([]);
  const [medications, setMedications] = useState("");
  const [dietHistory, setDietHistory] = useState("");
  const [direction, setDirection] = useState<"lose" | "gain" | "recomp">("lose");
  const [desiredWeight, setDesiredWeight] = useState("");
  const [timeline, setTimeline] = useState(16);
  const [motivation, setMotivation] = useState("health");

  const steps = ["Basics", "Activity & Setup", "Health", "Goal & Timeline", "Motivation"];
  const progress = (step + 1) / steps.length;

  const canNext = () => {
    if (step === 0) return Number(weight) > 25;
    return true;
  };

  const submit = async () => {
    setBusy(true);
    try {
      await api.post("/onboarding/profile", {
        weight_kg: Number(weight), body_frame: frame, activity_level: activity,
        training_environment: env, home_equipment: env === "home_equipment" ? equipment : [],
        conditions, medications_text: medications, injuries_text: injuries,
        diet_history: dietHistory ? [{ text: dietHistory }] : [], motivation,
        direction, desired_weight_kg: desiredWeight ? Number(desiredWeight) : null,
        timeline_weeks: timeline, same_place_every_workout: samePlace,
        environment_schedule: samePlace ? {} : schedule,
      });
      await refresh();
      router.replace("/photo");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen>
      <View style={{ paddingTop: insets.top + spacing.md, paddingHorizontal: spacing.lg }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: spacing.md }}>
          <Feather name="chevron-left" size={26} color={colors.textPrimary} onPress={() => (step === 0 ? router.back() : setStep(step - 1))} />
          <View style={{ flex: 1, height: 4, borderRadius: 2, backgroundColor: colors.surface }}>
            <View style={{ width: `${progress * 100}%`, height: 4, borderRadius: 2, backgroundColor: colors.accentTeal }} />
          </View>
        </View>
        <Text style={{ color: colors.textSecondary, fontSize: font.size.xs, marginTop: spacing.sm, letterSpacing: 1.5, textTransform: "uppercase" }}>
          Step {step + 1} of {steps.length} · {steps[step]}
        </Text>
      </View>

      <KeyboardAwareScrollView bottomOffset={90} contentContainerStyle={{ paddingHorizontal: spacing.lg, paddingTop: spacing.lg, paddingBottom: insets.bottom + 100 }}>
        {step === 0 && (
          <View style={{ gap: spacing.lg }}>
            <TextField testID="ob-weight" label="Current weight (kg)" value={weight} onChangeText={setWeight} placeholder="e.g. 82" keyboardType="numeric" />
            <OptionGroup label="Body frame" testIDPrefix="ob-frame" value={frame} onChange={setFrame}
              options={[{ value: "small", label: "Small" }, { value: "medium", label: "Medium" }, { value: "large", label: "Large" }]} />
            <Text style={{ color: colors.textTertiary, fontSize: font.size.xs }}>
              Frame (wrist/ankle size) helps set a realistic lean-mass ceiling.
            </Text>
          </View>
        )}

        {step === 1 && (
          <View style={{ gap: spacing.lg }}>
            <OptionGroup label="Activity level" testIDPrefix="ob-activity" value={activity} onChange={setActivity}
              options={[
                { value: "sedentary", label: "Sedentary" }, { value: "light", label: "Light" },
                { value: "moderate", label: "Moderate" }, { value: "active", label: "Active" },
                { value: "very_active", label: "Very active" },
              ]} />
            <OptionGroup label="Training environment" testIDPrefix="ob-env" value={env} onChange={setEnv}
              options={[
                { value: "gym", label: ENV_LABELS.gym },
                { value: "home_equipment", label: ENV_LABELS.home_equipment },
                { value: "home_no_equipment", label: ENV_LABELS.home_no_equipment },
              ]} />
            {env === "home_equipment" && (
              <OptionGroup label="What equipment do you have?" multi testIDPrefix="ob-equip"
                value={equipment} onChange={setEquipment}
                options={EQUIPMENT.map((e) => ({ value: e, label: e }))} />
            )}
            <OptionGroup label="Same place every workout?" testIDPrefix="ob-sameplace"
              value={samePlace ? "yes" : "no"} onChange={(v: string) => setSamePlace(v === "yes")}
              options={[{ value: "yes", label: "Yes, always" }, { value: "no", label: "No, it varies" }]} />
            {!samePlace && (
              <View style={{ gap: spacing.sm }}>
                <Label>Assign an environment per day</Label>
                {WEEKDAYS.map((d) => (
                  <View key={d} style={{ gap: 4 }}>
                    <Text style={{ color: colors.textSecondary, fontSize: font.size.sm }}>{d}</Text>
                    <OptionGroup testIDPrefix={`ob-sched-${d}`} value={schedule[d] || env}
                      onChange={(v: string) => setSchedule((s) => ({ ...s, [d]: v }))}
                      options={[
                        { value: "gym", label: "Gym" }, { value: "home_equipment", label: "Home+" },
                        { value: "home_no_equipment", label: "Home" },
                      ]} />
                  </View>
                ))}
              </View>
            )}
            <TextField testID="ob-injuries" label="Injuries or limitations (optional)" value={injuries} onChangeText={setInjuries} placeholder="e.g. left knee, lower-back sensitivity" />
          </View>
        )}

        {step === 2 && (
          <View style={{ gap: spacing.lg }}>
            <OptionGroup label="Conditions (select all that apply)" multi testIDPrefix="ob-cond"
              value={conditions} onChange={setConditions}
              options={Object.entries(CONDITION_LABELS).map(([value, label]) => ({ value, label }))} />
            <TextField testID="ob-meds" label="Medications (optional)" value={medications} onChangeText={setMedications} placeholder="e.g. levothyroxine, metformin" />
            <TextField testID="ob-diet-history" label="What have you tried, and why did it stall?" value={dietHistory} onChangeText={setDietHistory} placeholder="e.g. keto — too restrictive to keep up" />
          </View>
        )}

        {step === 3 && (
          <View style={{ gap: spacing.lg }}>
            <OptionGroup label="Goal direction" testIDPrefix="ob-direction" value={direction} onChange={setDirection}
              options={[{ value: "lose", label: "Lose fat" }, { value: "gain", label: "Gain muscle" }, { value: "recomp", label: "Recomp" }]} />
            {direction !== "recomp" && (
              <TextField testID="ob-desired" label="Desired weight (kg, optional)" value={desiredWeight} onChangeText={setDesiredWeight} placeholder="e.g. 74" keyboardType="numeric" />
            )}
            <View>
              <Label>Timeline</Label>
              <View style={{ marginTop: spacing.sm, marginBottom: spacing.xs }}>
                <StatReadout value={timeline} unit="weeks" label="target horizon" />
              </View>
              <Slider testID="ob-timeline" minimumValue={8} maximumValue={52} step={1} value={timeline}
                onValueChange={(v) => setTimeline(Math.round(v))}
                minimumTrackTintColor={colors.accentTeal} maximumTrackTintColor={colors.border}
                thumbTintColor={colors.accentBlue} />
              <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
                <Text style={{ color: colors.textTertiary, fontSize: font.size.xs }}>8 wks</Text>
                <Text style={{ color: colors.textTertiary, fontSize: font.size.xs }}>52 wks</Text>
              </View>
            </View>
          </View>
        )}

        {step === 4 && (
          <View style={{ gap: spacing.lg }}>
            <OptionGroup label="What's driving this for you?" testIDPrefix="ob-motivation" value={motivation} onChange={setMotivation}
              options={[
                { value: "health", label: "Health" }, { value: "appearance", label: "Appearance" },
                { value: "family", label: "Family" }, { value: "performance", label: "Performance" },
                { value: "other", label: "Other" },
              ]} />
            <Text style={{ color: colors.textSecondary, fontSize: font.size.sm, lineHeight: 20 }}>
              Next, we'll take a full-body photo and generate three realistic targets — bounded by
              what your age, sex, frame, conditions and timeline actually allow.
            </Text>
          </View>
        )}
      </KeyboardAwareScrollView>

      <View style={{ position: "absolute", left: spacing.lg, right: spacing.lg, bottom: insets.bottom + spacing.md }}>
        <GradientButton
          testID="ob-next"
          label={step === steps.length - 1 ? "Continue to photo" : "Continue"}
          loading={busy} disabled={!canNext()}
          onPress={() => (step === steps.length - 1 ? submit() : setStep(step + 1))}
        />
      </View>
    </Screen>
  );
}

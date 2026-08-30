import { useState } from "react";
import { Text, View } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { Feather } from "@expo/vector-icons";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAuth } from "@/src/context/AuthContext";
import { GradientButton, Label, Screen } from "@/src/components/ui";
import { TextField, OptionGroup, CheckRow } from "@/src/components/form";

function validDob(s: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(s) && !isNaN(Date.parse(s));
}
function age(dob: string): number {
  const d = new Date(dob), t = new Date();
  let a = t.getFullYear() - d.getFullYear();
  if (t.getMonth() < d.getMonth() || (t.getMonth() === d.getMonth() && t.getDate() < d.getDate())) a--;
  return a;
}

export default function Signup() {
  const router = useRouter();
  const { colors, spacing, font } = useTheme();
  const insets = useSafeAreaInsets();
  const { signup } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [dob, setDob] = useState("");
  const [sex, setSex] = useState<"male" | "female">("male");
  const [heightCm, setHeightCm] = useState("");
  const [unit, setUnit] = useState<"metric" | "imperial">("metric");
  const [ackAge, setAckAge] = useState(false);
  const [ackPhysician, setAckPhysician] = useState(false);
  const [ackPrivacy, setAckPrivacy] = useState(false);
  const [pregnant, setPregnant] = useState(false);
  const [edHistory, setEdHistory] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const canSubmit =
    /\S+@\S+\.\S+/.test(email) && password.length >= 8 && validDob(dob) &&
    Number(heightCm) > 80 && ackAge && ackPhysician && ackPrivacy;

  const onSubmit = async () => {
    setErr(null);
    if (!validDob(dob)) return setErr("Enter date of birth as YYYY-MM-DD");
    if (age(dob) < 18) return setErr("You must be at least 18 to use TrueForm");
    setBusy(true);
    try {
      await signup({
        email: email.trim().toLowerCase(), password, dob, sex,
        height_cm: Number(heightCm), unit_preference: unit,
        consent: {
          age_confirmed_18: ackAge, physician_ack: ackPhysician, privacy_ack: ackPrivacy,
          is_pregnant: pregnant, eating_disorder_history: edHistory,
        },
      });
      router.replace("/onboarding");
    } catch (e: any) {
      setErr(e?.detail || e?.message || "Could not create account");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen>
      <KeyboardAwareScrollView
        bottomOffset={90}
        contentContainerStyle={{ paddingTop: insets.top + spacing.md, paddingHorizontal: spacing.lg, paddingBottom: insets.bottom + 100 }}
      >
        <Feather name="chevron-left" size={26} color={colors.textPrimary} onPress={() => router.back()} />
        <Text style={{ color: colors.textPrimary, fontSize: font.size["2xl"], fontWeight: "200", marginTop: spacing.md }}>
          Create your account
        </Text>
        <Text style={{ color: colors.textSecondary, marginTop: 4, marginBottom: spacing.lg }}>
          Adults 18+. We verify your age.
        </Text>

        <View style={{ gap: spacing.md }}>
          <TextField testID="signup-email" label="Email" value={email} onChangeText={setEmail} placeholder="you@example.com" keyboardType="email-address" autoCapitalize="none" />
          <TextField testID="signup-password" label="Password (min 8 chars)" value={password} onChangeText={setPassword} placeholder="••••••••" secureTextEntry />
          <TextField testID="signup-dob" label="Date of birth" value={dob} onChangeText={setDob} placeholder="YYYY-MM-DD" keyboardType="numbers-and-punctuation" autoCapitalize="none" />
          <OptionGroup label="Sex (for medical accuracy)" testIDPrefix="signup-sex" value={sex} onChange={setSex} options={[{ value: "male", label: "Male" }, { value: "female", label: "Female" }]} />
          <OptionGroup label="Units" testIDPrefix="signup-unit" value={unit} onChange={setUnit} options={[{ value: "metric", label: "Metric (kg/cm)" }, { value: "imperial", label: "Imperial (lb/ft)" }]} />
          <TextField testID="signup-height" label="Height in cm" value={heightCm} onChangeText={setHeightCm} placeholder="e.g. 175" keyboardType="numeric" />
        </View>

        <View style={{ marginTop: spacing.lg }}>
          <Label>Consent</Label>
          <CheckRow testID="signup-ack-age" label="I confirm I am 18 years or older." checked={ackAge} onToggle={() => setAckAge((v) => !v)} />
          <CheckRow testID="signup-ack-physician" label="I have consulted, or will consult, a physician before starting a diet or exercise plan." checked={ackPhysician} onToggle={() => setAckPhysician((v) => !v)} />
          <CheckRow testID="signup-ack-privacy" label="I understand my photos are private, encrypted, never used for training, and deletable anytime." checked={ackPrivacy} onToggle={() => setAckPrivacy((v) => !v)} />
        </View>

        <View style={{ marginTop: spacing.md }}>
          <Label>Health & safety (optional but important)</Label>
          <CheckRow testID="signup-pregnant" label="I am currently pregnant." checked={pregnant} onToggle={() => setPregnant((v) => !v)} />
          <CheckRow testID="signup-ed" label="I have a history of an eating disorder." checked={edHistory} onToggle={() => setEdHistory((v) => !v)} />
          <Text style={{ color: colors.textTertiary, fontSize: font.size.xs, lineHeight: 16, marginTop: 4 }}>
            If either applies, we won't generate a plan — we'll show supportive resources instead.
          </Text>
        </View>

        {err ? <Text testID="signup-error" style={{ color: colors.alert, marginTop: spacing.md }}>{err}</Text> : null}
      </KeyboardAwareScrollView>

      <View style={{ position: "absolute", left: spacing.lg, right: spacing.lg, bottom: insets.bottom + spacing.md }}>
        <GradientButton testID="signup-submit" label="Create account" loading={busy} disabled={!canSubmit} onPress={onSubmit} />
      </View>
    </Screen>
  );
}

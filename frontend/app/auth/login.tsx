import { useState } from "react";
import { Text, View } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { Feather } from "@expo/vector-icons";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAuth } from "@/src/context/AuthContext";
import { GradientButton, Screen } from "@/src/components/ui";
import { TextField } from "@/src/components/form";

export default function Login() {
  const router = useRouter();
  const { colors, spacing, font } = useTheme();
  const insets = useSafeAreaInsets();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onSubmit = async () => {
    setErr(null);
    setBusy(true);
    try {
      await login(email.trim().toLowerCase(), password);
      router.replace("/");
    } catch (e: any) {
      setErr(e?.detail || e?.message || "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen>
      <KeyboardAwareScrollView
        bottomOffset={90}
        contentContainerStyle={{ paddingTop: insets.top + spacing.md, paddingHorizontal: spacing.lg, flexGrow: 1 }}
      >
        <Feather name="chevron-left" size={26} color={colors.textPrimary} onPress={() => router.back()} />
        <Text style={{ color: colors.textPrimary, fontSize: font.size["2xl"], fontWeight: "200", marginTop: spacing.md, marginBottom: spacing.lg }}>
          Welcome back
        </Text>
        <View style={{ gap: spacing.md }}>
          <TextField testID="login-email" label="Email" value={email} onChangeText={setEmail} placeholder="you@example.com" keyboardType="email-address" autoCapitalize="none" />
          <TextField testID="login-password" label="Password" value={password} onChangeText={setPassword} placeholder="••••••••" secureTextEntry />
        </View>
        {err ? <Text testID="login-error" style={{ color: colors.alert, marginTop: spacing.md }}>{err}</Text> : null}
        <View style={{ marginTop: spacing.xl }}>
          <GradientButton testID="login-submit" label="Log in" loading={busy} disabled={!email || !password} onPress={onSubmit} />
        </View>
      </KeyboardAwareScrollView>
    </Screen>
  );
}

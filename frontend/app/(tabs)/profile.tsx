import { useState } from "react";
import { Platform, ScrollView, Share, Switch, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import * as Notifications from "expo-notifications";
import { Feather } from "@expo/vector-icons";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAuth } from "@/src/context/AuthContext";
import { api } from "@/src/api/client";
import { Card, Chip, Label, OutlineButton, Screen, MedicalDisclaimer } from "@/src/components/ui";
import { OptionGroup } from "@/src/components/form";

const TIMES = ["07:00", "08:00", "12:00", "18:00", "20:00"];

async function scheduleDaily(time: string, enabled: boolean) {
  try {
    await Notifications.cancelAllScheduledNotificationsAsync();
    if (!enabled) return;
    const perm = await Notifications.requestPermissionsAsync();
    if (!perm.granted) return;
    const [h, m] = time.split(":").map(Number);
    await Notifications.scheduleNotificationAsync({
      content: { title: "TrueForm", body: "Time to log today — meals, workout, how you feel." },
      trigger: { type: Notifications.SchedulableTriggerInputTypes.DAILY, hour: h, minute: m },
    });
  } catch {
    // Local scheduling is limited in Expo Go; works in a native build.
  }
}

export default function ProfileScreen() {
  const router = useRouter();
  const { colors, spacing, font } = useTheme();
  const insets = useSafeAreaInsets();
  const { user, setUser, logout } = useAuth();

  const [confirmDelete, setConfirmDelete] = useState(false);
  const [busy, setBusy] = useState(false);

  const patch = async (body: any) => {
    const updated = await api.patch<any>("/settings", body);
    setUser(updated);
  };

  const exportData = async () => {
    const data = await api.get<any>("/account/export");
    await Share.share({ message: JSON.stringify(data, null, 2) });
  };

  const doDelete = async () => {
    setBusy(true);
    try {
      await api.del("/account");
      await logout();
      router.replace("/welcome");
    } finally { setBusy(false); }
  };

  if (!user) return <Screen><View style={{ flex: 1 }} /></Screen>;

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ paddingTop: insets.top + spacing.md, paddingHorizontal: spacing.lg, paddingBottom: spacing.xl }}>
        <Label>Profile</Label>
        <Text style={{ color: colors.textPrimary, fontSize: font.size.xl, fontWeight: "200" }}>{user.email}</Text>
        <Text style={{ color: colors.textTertiary, fontSize: font.size.sm, marginTop: 2 }}>
          {user.sex} · target: {user.chosen_target || "not chosen"}
        </Text>

        {/* Preferences */}
        <View style={{ marginTop: spacing.lg }}>
          <Label>Preferences</Label>
          <Card style={{ marginTop: spacing.sm, gap: spacing.md }}>
            <OptionGroup label="Units" testIDPrefix="settings-unit" value={user.unit_preference}
              onChange={(v: string) => patch({ unit_preference: v })}
              options={[{ value: "metric", label: "Metric (kg/cm)" }, { value: "imperial", label: "Imperial (lb/ft)" }]} />

            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
              <Text style={{ color: colors.textPrimary }}>Daily reminder</Text>
              <Switch testID="settings-notif-toggle" value={user.notifications_enabled}
                onValueChange={async (v) => { await patch({ notifications_enabled: v }); scheduleDaily(user.notification_time, v); }}
                trackColor={{ true: colors.accentTeal, false: colors.border }} />
            </View>
            {user.notifications_enabled ? (
              <View style={{ flexDirection: "row", flexWrap: "wrap", gap: spacing.sm }}>
                {TIMES.map((t) => (
                  <Chip key={t} testID={`settings-time-${t}`} label={t} active={user.notification_time === t}
                    onPress={async () => { await patch({ notification_time: t }); scheduleDaily(t, true); }} />
                ))}
              </View>
            ) : null}
            <Text style={{ color: colors.textTertiary, fontSize: font.size.xs }}>
              Reminders fire on-device. Full push works in a native build after publishing.
            </Text>
          </Card>
        </View>

        {/* Data */}
        <View style={{ marginTop: spacing.lg }}>
          <Label>Your data</Label>
          <Card style={{ marginTop: spacing.sm, gap: spacing.sm }}>
            <OutlineButton testID="settings-export" label="Export my data" onPress={exportData} />
            <Text style={{ color: colors.textTertiary, fontSize: font.size.xs }}>
              Photos are private, encrypted at rest, and never used for training.
            </Text>
          </Card>
        </View>

        {/* Danger zone */}
        <View style={{ marginTop: spacing.lg }}>
          <Label>Account</Label>
          <Card style={{ marginTop: spacing.sm, gap: spacing.sm }}>
            <OutlineButton testID="settings-logout" label="Log out" onPress={async () => { await logout(); router.replace("/welcome"); }} />
            {!confirmDelete ? (
              <OutlineButton testID="settings-delete" tone="danger" label="Delete account & all photos" onPress={() => setConfirmDelete(true)} />
            ) : (
              <View style={{ gap: spacing.sm }}>
                <Text style={{ color: colors.alert, fontSize: font.size.sm }}>This permanently deletes your account, plan, logs and photos. This cannot be undone.</Text>
                <OutlineButton testID="settings-delete-confirm" tone="danger" label={busy ? "Deleting…" : "Yes, delete everything"} onPress={doDelete} />
                <OutlineButton testID="settings-delete-cancel" label="Cancel" onPress={() => setConfirmDelete(false)} />
              </View>
            )}
          </Card>
        </View>

        <View style={{ marginTop: spacing.lg }}>
          <MedicalDisclaimer />
          <Text style={{ color: colors.textTertiary, fontSize: font.size.xs, marginTop: spacing.sm, textAlign: "center" }}>
            Exercise media: wger.de community (CC-BY-SA 4.0)
          </Text>
        </View>
      </ScrollView>
    </Screen>
  );
}

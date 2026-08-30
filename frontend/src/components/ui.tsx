import React from "react";
import {
  ActivityIndicator, Pressable, StyleSheet, Text, TextStyle, View, ViewStyle,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Feather } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";

import { useTheme } from "@/src/theme/ThemeContext";
import { ACCENT_GRADIENT } from "@/src/theme/tokens";

// ---- Primary gradient button ------------------------------------------------
export function GradientButton({
  label, onPress, disabled, loading, testID, icon,
}: {
  label: string; onPress: () => void; disabled?: boolean; loading?: boolean;
  testID?: string; icon?: keyof typeof Feather.glyphMap;
}) {
  const { radius, font, colors } = useTheme();
  return (
    <Pressable
      testID={testID}
      disabled={disabled || loading}
      onPress={() => { Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium); onPress(); }}
      style={{ opacity: disabled ? 0.4 : 1 }}
    >
      <LinearGradient
        colors={ACCENT_GRADIENT as any}
        start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
        style={{
          height: 54, borderRadius: radius.md, alignItems: "center",
          justifyContent: "center", flexDirection: "row", gap: 8,
        }}
      >
        {loading ? (
          <ActivityIndicator color={colors.onAccent} />
        ) : (
          <>
            {icon ? <Feather name={icon} size={18} color={colors.onAccent} /> : null}
            <Text style={{ color: colors.onAccent, fontWeight: "700", fontSize: font.size.md }}>
              {label}
            </Text>
          </>
        )}
      </LinearGradient>
    </Pressable>
  );
}

// ---- Secondary / outline button ---------------------------------------------
export function OutlineButton({
  label, onPress, testID, tone = "default",
}: { label: string; onPress: () => void; testID?: string; tone?: "default" | "danger" }) {
  const { colors, radius, font } = useTheme();
  const c = tone === "danger" ? colors.alert : colors.textPrimary;
  return (
    <Pressable
      testID={testID} onPress={onPress}
      style={{
        height: 52, borderRadius: radius.md, borderWidth: 1,
        borderColor: tone === "danger" ? colors.alert : colors.border,
        alignItems: "center", justifyContent: "center",
      }}
    >
      <Text style={{ color: c, fontWeight: "600", fontSize: font.size.base }}>{label}</Text>
    </Pressable>
  );
}

// ---- Stat readout (big thin numeral + uppercase label) ----------------------
export function StatReadout({
  value, unit, label, align = "left", size,
}: { value: string | number; unit?: string; label: string; align?: "left" | "center"; size?: number }) {
  const { colors, font } = useTheme();
  return (
    <View style={{ alignItems: align === "center" ? "center" : "flex-start" }}>
      <View style={{ flexDirection: "row", alignItems: "flex-end" }}>
        <Text style={{ color: colors.textPrimary, fontSize: size ?? font.size["3xl"], fontWeight: font.numeral }}>
          {value}
        </Text>
        {unit ? (
          <Text style={{ color: colors.textSecondary, fontSize: font.size.md, fontWeight: "300", marginBottom: 8, marginLeft: 4 }}>
            {unit}
          </Text>
        ) : null}
      </View>
      <Text style={{
        color: colors.textSecondary, fontSize: font.size.xs, fontWeight: font.label,
        letterSpacing: font.letterSpacingLabel, textTransform: "uppercase", marginTop: 2,
      }}>
        {label}
      </Text>
    </View>
  );
}

// ---- Uppercase section label ------------------------------------------------
export function Label({ children, style }: { children: React.ReactNode; style?: TextStyle }) {
  const { colors, font } = useTheme();
  return (
    <Text style={[{
      color: colors.textSecondary, fontSize: font.size.xs, fontWeight: font.label,
      letterSpacing: font.letterSpacingLabel, textTransform: "uppercase",
    }, style]}>
      {children}
    </Text>
  );
}

// ---- Card -------------------------------------------------------------------
export function Card({ children, style, testID }: { children: React.ReactNode; style?: ViewStyle; testID?: string }) {
  const { colors, radius, spacing } = useTheme();
  return (
    <View testID={testID} style={[{
      backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1,
      borderColor: colors.border, padding: spacing.md,
    }, style]}>
      {children}
    </View>
  );
}

// ---- Pill chip (filter / toggle) --------------------------------------------
export function Chip({
  label, active, onPress, testID,
}: { label: string; active?: boolean; onPress?: () => void; testID?: string }) {
  const { colors, radius, font } = useTheme();
  return (
    <Pressable
      testID={testID}
      onPress={() => { Haptics.selectionAsync(); onPress?.(); }}
      style={{
        height: 36, paddingHorizontal: 16, borderRadius: radius.pill, flexShrink: 0,
        alignItems: "center", justifyContent: "center", borderWidth: 1,
        borderColor: active ? colors.accentTeal : colors.border,
        backgroundColor: active ? colors.accentTeal : "transparent",
      }}
    >
      <Text style={{
        color: active ? colors.onAccent : colors.textSecondary,
        fontSize: font.size.sm, fontWeight: "600",
      }}>
        {label}
      </Text>
    </Pressable>
  );
}

// ---- Flat list row with hairline divider + trailing status ------------------
export function ListRow({
  title, subtitle, status, onPress, right, testID, icon,
}: {
  title: string; subtitle?: string; status?: "confirmed" | "rescheduled" | null;
  onPress?: () => void; right?: React.ReactNode; testID?: string;
  icon?: keyof typeof Feather.glyphMap;
}) {
  const { colors, font, spacing } = useTheme();
  return (
    <Pressable
      testID={testID} onPress={onPress}
      style={{
        flexDirection: "row", alignItems: "center", paddingVertical: spacing.md,
        borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border, gap: 12,
      }}
    >
      {icon ? <Feather name={icon} size={18} color={colors.textSecondary} /> : null}
      <View style={{ flex: 1 }}>
        <Text style={{ color: colors.textPrimary, fontSize: font.size.md, fontWeight: "500" }}>{title}</Text>
        {subtitle ? <Text style={{ color: colors.textSecondary, fontSize: font.size.sm, marginTop: 2 }}>{subtitle}</Text> : null}
      </View>
      {right}
      {status === "confirmed" ? <Feather name="check" size={20} color={colors.success} /> : null}
      {status === "rescheduled" ? (
        <Text style={{ color: colors.textTertiary, fontSize: font.size.xs, fontWeight: "600" }}>RESCHEDULED</Text>
      ) : null}
    </Pressable>
  );
}

// ---- Checkbox with haptic ----------------------------------------------------
export function CheckBox({ checked, onToggle, testID }: { checked: boolean; onToggle: () => void; testID?: string }) {
  const { colors, radius } = useTheme();
  return (
    <Pressable
      testID={testID}
      onPress={() => { Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success); onToggle(); }}
      hitSlop={10}
      style={{
        width: 28, height: 28, borderRadius: radius.sm, borderWidth: 1.5,
        borderColor: checked ? colors.accentTeal : colors.borderStrong,
        backgroundColor: checked ? colors.accentTeal : "transparent",
        alignItems: "center", justifyContent: "center",
      }}
    >
      {checked ? <Feather name="check" size={18} color={colors.onAccent} /> : null}
    </Pressable>
  );
}

// ---- Skeleton loader (no spinners) ------------------------------------------
export function Skeleton({ height = 16, width = "100%", radius: r }: { height?: number; width?: any; radius?: number }) {
  const { colors, radius } = useTheme();
  return (
    <View style={{ height, width, borderRadius: r ?? radius.sm, backgroundColor: colors.surfaceElevated, opacity: 0.6 }} />
  );
}

// ---- Medical disclaimer ------------------------------------------------------
export function MedicalDisclaimer({ style }: { style?: ViewStyle }) {
  const { colors, font, spacing, radius } = useTheme();
  return (
    <View style={[{
      flexDirection: "row", gap: 8, padding: spacing.sm, borderRadius: radius.sm,
      backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border,
    }, style]}>
      <Feather name="info" size={14} color={colors.textTertiary} style={{ marginTop: 2 }} />
      <Text style={{ color: colors.textTertiary, fontSize: font.size.xs, flex: 1, lineHeight: 16 }}>
        Estimates for guidance only — not medical advice. Consult your physician before starting
        any diet or exercise program.
      </Text>
    </View>
  );
}

export function Screen({ children, style }: { children: React.ReactNode; style?: ViewStyle }) {
  const { colors } = useTheme();
  return <View style={[{ flex: 1, backgroundColor: colors.bg }, style]}>{children}</View>;
}

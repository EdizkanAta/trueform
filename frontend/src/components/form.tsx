import React from "react";
import { Pressable, Text, TextInput, View, ViewStyle } from "react-native";
import { Feather } from "@expo/vector-icons";

import { useTheme } from "@/src/theme/ThemeContext";
import { Label } from "@/src/components/ui";

export function TextField({
  label, value, onChangeText, placeholder, secureTextEntry, keyboardType, autoCapitalize, testID, error,
}: {
  label?: string; value: string; onChangeText: (t: string) => void; placeholder?: string;
  secureTextEntry?: boolean; keyboardType?: any; autoCapitalize?: any; testID?: string; error?: string;
}) {
  const { colors, radius, font, spacing } = useTheme();
  return (
    <View style={{ gap: 6 }}>
      {label ? <Label>{label}</Label> : null}
      <TextInput
        testID={testID}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={colors.textTertiary}
        secureTextEntry={secureTextEntry}
        keyboardType={keyboardType}
        autoCapitalize={autoCapitalize}
        style={{
          height: 52, borderRadius: radius.sm, borderWidth: 1,
          borderColor: error ? colors.alert : colors.border, backgroundColor: colors.surface,
          paddingHorizontal: spacing.md, color: colors.textPrimary, fontSize: font.size.md,
        }}
      />
      {error ? <Text style={{ color: colors.alert, fontSize: font.size.xs }}>{error}</Text> : null}
    </View>
  );
}

// Segmented single/multi select of pill options.
export function OptionGroup<T extends string>({
  label, options, value, onChange, multi, testIDPrefix,
}: {
  label?: string; options: { value: T; label: string }[]; value: T | T[];
  onChange: (v: any) => void; multi?: boolean; testIDPrefix?: string;
}) {
  const { colors, radius, font, spacing } = useTheme();
  const selected = (v: T) => (multi ? (value as T[]).includes(v) : value === v);
  const toggle = (v: T) => {
    if (multi) {
      const arr = value as T[];
      onChange(arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);
    } else onChange(v);
  };
  return (
    <View style={{ gap: 8 }}>
      {label ? <Label>{label}</Label> : null}
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: spacing.sm }}>
        {options.map((o) => {
          const on = selected(o.value);
          return (
            <Pressable
              key={o.value}
              testID={testIDPrefix ? `${testIDPrefix}-${o.value}` : undefined}
              onPress={() => toggle(o.value)}
              style={{
                paddingHorizontal: 14, paddingVertical: 10, borderRadius: radius.pill,
                borderWidth: 1, borderColor: on ? colors.accentTeal : colors.border,
                backgroundColor: on ? colors.accentTeal : "transparent",
              }}
            >
              <Text style={{ color: on ? colors.onAccent : colors.textSecondary, fontSize: font.size.sm, fontWeight: "600" }}>
                {o.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

// Consent / boolean row with a checkbox.
export function CheckRow({
  label, checked, onToggle, testID, style,
}: { label: string; checked: boolean; onToggle: () => void; testID?: string; style?: ViewStyle }) {
  const { colors, radius, font, spacing } = useTheme();
  return (
    <Pressable
      testID={testID} onPress={onToggle}
      style={[{ flexDirection: "row", gap: spacing.md, alignItems: "flex-start", paddingVertical: spacing.sm }, style]}
    >
      <View style={{
        width: 24, height: 24, borderRadius: radius.sm, borderWidth: 1.5,
        borderColor: checked ? colors.accentTeal : colors.borderStrong,
        backgroundColor: checked ? colors.accentTeal : "transparent",
        alignItems: "center", justifyContent: "center", marginTop: 1,
      }}>
        {checked ? <Feather name="check" size={16} color={colors.onAccent} /> : null}
      </View>
      <Text style={{ color: colors.textSecondary, fontSize: font.size.base, flex: 1, lineHeight: 20 }}>{label}</Text>
    </Pressable>
  );
}

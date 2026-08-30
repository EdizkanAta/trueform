import React from "react";
import { Pressable, Text, View, ViewStyle } from "react-native";
import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";

import { useTheme } from "@/src/theme/ThemeContext";

// Full-bleed image card with a dark gradient scrim and left-aligned title.
export function FullBleedCard({
  imageUri, title, subtitle, height = 160, onPress, children, testID, style,
}: {
  imageUri?: string; title: string; subtitle?: string; height?: number;
  onPress?: () => void; children?: React.ReactNode; testID?: string; style?: ViewStyle;
}) {
  const { colors, radius, font, spacing } = useTheme();
  return (
    <Pressable testID={testID} onPress={onPress} style={[{
      height, borderRadius: radius.md, overflow: "hidden", backgroundColor: colors.surface,
      borderWidth: 1, borderColor: colors.border,
    }, style]}>
      {imageUri ? (
        <Image source={{ uri: imageUri }} style={{ ...StyleSheetAbsolute }} contentFit="cover" transition={200} />
      ) : null}
      <LinearGradient
        colors={["transparent", colors.scrim, colors.bg]}
        style={{ ...StyleSheetAbsolute }}
      />
      <View style={{ flex: 1, justifyContent: "flex-end", padding: spacing.md }}>
        {children}
        <Text style={{ color: colors.textPrimary, fontSize: font.size.lg, fontWeight: "600" }}>{title}</Text>
        {subtitle ? (
          <Text style={{ color: colors.textSecondary, fontSize: font.size.sm, marginTop: 2 }}>{subtitle}</Text>
        ) : null}
      </View>
    </Pressable>
  );
}

const StyleSheetAbsolute = {
  position: "absolute" as const, top: 0, left: 0, right: 0, bottom: 0,
};

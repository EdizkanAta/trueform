import React from "react";
import { View, Text, LayoutChangeEvent } from "react-native";
import { Image } from "expo-image";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import Animated, {
  useAnimatedStyle, useSharedValue, runOnJS,
} from "react-native-reanimated";
import { Feather } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";

import { useTheme } from "@/src/theme/ThemeContext";

// Side-by-side comparison with a draggable vertical divider.
// Left = base photo (fixed), Right layer (clipped) = comparison image.
export function ComparisonViewer({
  leftUri, rightUri, leftLabel, rightLabel, height = 380,
}: {
  leftUri?: string; rightUri?: string; leftLabel: string; rightLabel: string; height?: number;
}) {
  const { colors, radius } = useTheme();
  const [width, setWidth] = React.useState(300);
  const divider = useSharedValue(150);

  const onLayout = (e: LayoutChangeEvent) => {
    const w = e.nativeEvent.layout.width;
    setWidth(w);
    divider.value = w / 2;
  };

  const tick = () => Haptics.selectionAsync();
  const pan = Gesture.Pan()
    .onChange((e) => {
      const next = divider.value + e.changeX;
      divider.value = Math.max(20, Math.min(width - 20, next));
    })
    .onEnd(() => runOnJS(tick)());

  const rightClip = useAnimatedStyle(() => ({ width: width - divider.value }));
  const handleStyle = useAnimatedStyle(() => ({ left: divider.value - 16 }));

  return (
    <View>
      <View
        onLayout={onLayout}
        style={{ height, borderRadius: radius.md, overflow: "hidden", backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border }}
      >
        {leftUri ? (
          <Image source={{ uri: leftUri }} style={{ width: "100%", height: "100%" }} contentFit="cover" />
        ) : (
          <View style={{ flex: 1, alignItems: "center", justifyContent: "center" }}>
            <Feather name="image" size={28} color={colors.textTertiary} />
          </View>
        )}

        <Animated.View style={[{ position: "absolute", top: 0, bottom: 0, right: 0, overflow: "hidden", alignItems: "flex-end" }, rightClip]}>
          {rightUri ? (
            <Image source={{ uri: rightUri }} style={{ width, height }} contentFit="cover" />
          ) : (
            <View style={{ width, height, alignItems: "center", justifyContent: "center", backgroundColor: colors.surfaceElevated }}>
              <Feather name="user" size={28} color={colors.textTertiary} />
            </View>
          )}
        </Animated.View>

        <GestureDetector gesture={pan}>
          <Animated.View style={[{ position: "absolute", top: 0, bottom: 0, width: 32, alignItems: "center", justifyContent: "center" }, handleStyle]}>
            <View style={{ position: "absolute", top: 0, bottom: 0, width: 2, backgroundColor: colors.accentTeal }} />
            <View style={{ width: 32, height: 32, borderRadius: 16, backgroundColor: colors.accentTeal, alignItems: "center", justifyContent: "center" }}>
              <Feather name="move" size={16} color={colors.onAccent} />
            </View>
          </Animated.View>
        </GestureDetector>

        <View style={{ position: "absolute", left: 10, bottom: 10 }}>
          <View style={{ backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.sm, paddingHorizontal: 8, paddingVertical: 4 }}>
            <Text style={{ color: colors.textPrimary, fontSize: 11, fontWeight: "700", letterSpacing: 1 }}>{leftLabel.toUpperCase()}</Text>
          </View>
        </View>
        <View style={{ position: "absolute", right: 10, bottom: 10 }}>
          <View style={{ backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, borderRadius: radius.sm, paddingHorizontal: 8, paddingVertical: 4 }}>
            <Text style={{ color: colors.textPrimary, fontSize: 11, fontWeight: "700", letterSpacing: 1 }}>{rightLabel.toUpperCase()}</Text>
          </View>
        </View>
      </View>
    </View>
  );
}

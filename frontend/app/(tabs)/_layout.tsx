import { Platform } from "react-native";
import { Tabs } from "expo-router";
import { Feather } from "@expo/vector-icons";

import { useTheme } from "@/src/theme/ThemeContext";

const isIOS26 = Platform.OS === "ios" && parseInt(String(Platform.Version), 10) >= 26;

export default function TabsLayout() {
  const { colors } = useTheme();

  if (isIOS26) {
    // Native liquid-glass tabs on iOS 26+ (production-ready despite the import path).
    const { NativeTabs, Icon, Label } = require("expo-router/unstable-native-tabs");
    return (
      <NativeTabs>
        <NativeTabs.Trigger name="index">
          <Icon sf="house" />
          <Label>Today</Label>
        </NativeTabs.Trigger>
        <NativeTabs.Trigger name="plan">
          <Icon sf="calendar" />
          <Label>Plan</Label>
        </NativeTabs.Trigger>
        <NativeTabs.Trigger name="coach">
          <Icon sf="message" />
          <Label>Coach</Label>
        </NativeTabs.Trigger>
        <NativeTabs.Trigger name="progress">
          <Icon sf="chart.line.uptrend.xyaxis" />
          <Label>Progress</Label>
        </NativeTabs.Trigger>
        <NativeTabs.Trigger name="profile">
          <Icon sf="person" />
          <Label>Profile</Label>
        </NativeTabs.Trigger>
      </NativeTabs>
    );
  }

  const icon = (name: keyof typeof Feather.glyphMap) =>
    ({ color, size }: { color: string; size: number }) => <Feather name={name} size={size} color={color} />;

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.accentTeal,
        tabBarInactiveTintColor: colors.textTertiary,
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
          ...(Platform.OS === "web" ? { height: 64 } : {}),
        },
        tabBarItemStyle: { alignSelf: "center" },
        tabBarLabelStyle: { fontSize: 11 },
      }}
    >
      <Tabs.Screen name="index" options={{ title: "Today", tabBarIcon: icon("home") }} />
      <Tabs.Screen name="plan" options={{ title: "Plan", tabBarIcon: icon("calendar") }} />
      <Tabs.Screen name="coach" options={{ title: "Coach", tabBarIcon: icon("message-circle") }} />
      <Tabs.Screen name="progress" options={{ title: "Progress", tabBarIcon: icon("trending-up") }} />
      <Tabs.Screen name="profile" options={{ title: "Profile", tabBarIcon: icon("user") }} />
    </Tabs>
  );
}

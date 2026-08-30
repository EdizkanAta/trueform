import { useCallback, useRef, useState } from "react";
import { ScrollView, Text, TextInput, View, Pressable, ActivityIndicator } from "react-native";
import { useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { KeyboardAvoidingView } from "react-native-keyboard-controller";
import { Feather } from "@expo/vector-icons";

import { useTheme } from "@/src/theme/ThemeContext";
import { overlay } from "@/src/theme/theme";
import { api } from "@/src/api/client";
import { Label, Screen } from "@/src/components/ui";

type Msg = { id: string; role: "user" | "assistant"; content: string; filtered?: string[] };

export default function CoachScreen() {
  const { colors, spacing, font, radius } = useTheme();
  const insets = useSafeAreaInsets();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<ScrollView>(null);

  const load = useCallback(async () => {
    const res = await api.get<{ messages: Msg[] }>("/coach/messages");
    setMessages(res.messages);
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: false }), 100);
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const send = async () => {
    const t = text.trim();
    if (!t || sending) return;
    setText("");
    setMessages((m) => [...m, { id: `tmp-${Date.now()}`, role: "user", content: t }]);
    setSending(true);
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 50);
    try {
      const res = await api.post<{ message: Msg }>("/coach/message", { text: t });
      setMessages((m) => [...m, res.message]);
    } catch (e: any) {
      setMessages((m) => [...m, { id: `err-${Date.now()}`, role: "assistant", content: e?.detail || "Coach is unavailable right now. Please try again." }]);
    } finally {
      setSending(false);
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 80);
    }
  };

  return (
    <Screen>
      <KeyboardAvoidingView behavior="translate-with-padding" keyboardVerticalOffset={0} style={{ flex: 1 }}>
        <View style={{ paddingTop: insets.top + spacing.md, paddingHorizontal: spacing.lg, paddingBottom: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.border }}>
          <Label>AI Coach</Label>
          <Text style={{ color: colors.textPrimary, fontSize: font.size.xl, fontWeight: "200" }}>Direct, warm, no shaming</Text>
        </View>

        <ScrollView ref={scrollRef} contentContainerStyle={{ padding: spacing.lg, gap: spacing.md }} keyboardShouldPersistTaps="handled">
          {messages.length === 0 ? (
            <View style={{ marginTop: spacing.xl, alignItems: "center", gap: 8 }}>
              <Feather name="message-circle" size={28} color={colors.textTertiary} />
              <Text style={{ color: colors.textSecondary, textAlign: "center", fontSize: font.size.sm, paddingHorizontal: spacing.xl }}>
                Tell me how today went. "I skipped lunch", "my knee hurts", "I'm exhausted" — I'll adjust the plan.
              </Text>
            </View>
          ) : null}
          {messages.map((m) => (
            <View key={m.id} testID={`coach-msg-${m.role}`} style={{ alignSelf: m.role === "user" ? "flex-end" : "flex-start", maxWidth: "88%" }}>
              <View style={{
                backgroundColor: m.role === "user" ? colors.accentBlue : colors.surface,
                borderWidth: m.role === "user" ? 0 : 1, borderColor: colors.border,
                borderRadius: radius.md, padding: spacing.md,
              }}>
                <Text style={{ color: m.role === "user" ? overlay.onImage : colors.textPrimary, fontSize: font.size.base, lineHeight: 21 }}>{m.content}</Text>
              </View>
              {m.filtered && m.filtered.length ? (
                <Text style={{ color: colors.textTertiary, fontSize: 10, marginTop: 3 }}>Safety filter applied</Text>
              ) : null}
            </View>
          ))}
          {sending ? (
            <View style={{ alignSelf: "flex-start", flexDirection: "row", gap: 8, alignItems: "center" }}>
              <ActivityIndicator size="small" color={colors.accentTeal} />
              <Text style={{ color: colors.textTertiary, fontSize: font.size.xs }}>Coach is thinking…</Text>
            </View>
          ) : null}
        </ScrollView>

        <View style={{ flexDirection: "row", gap: spacing.sm, padding: spacing.md, paddingBottom: insets.bottom + spacing.sm, borderTopWidth: 1, borderTopColor: colors.border, alignItems: "flex-end" }}>
          <TextInput
            testID="coach-input"
            value={text} onChangeText={setText} placeholder="Message your coach…"
            placeholderTextColor={colors.textTertiary} multiline
            style={{ flex: 1, maxHeight: 120, minHeight: 44, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface, color: colors.textPrimary, paddingHorizontal: spacing.md, paddingTop: 12 }}
          />
          <Pressable testID="coach-send" onPress={send} disabled={!text.trim() || sending}
            style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: colors.accentTeal, alignItems: "center", justifyContent: "center", opacity: !text.trim() || sending ? 0.4 : 1 }}>
            <Feather name="arrow-up" size={20} color={colors.onAccent} />
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </Screen>
  );
}

import { useCallback, useState } from "react";
import { ScrollView, Text, View } from "react-native";
import { useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import * as ImagePicker from "expo-image-picker";

import { useTheme } from "@/src/theme/ThemeContext";
import { useAuth } from "@/src/context/AuthContext";
import { api, fileUrl, uploadPhoto } from "@/src/api/client";
import { Card, Chip, GradientButton, Label, Screen, StatReadout, MedicalDisclaimer } from "@/src/components/ui";
import { ComparisonViewer } from "@/src/components/ComparisonViewer";
import { LineChart } from "@/src/components/LineChart";
import { TextField } from "@/src/components/form";
import { kgToDisplay } from "@/src/lib/format";

export default function ProgressScreen() {
  const { colors, spacing, font } = useTheme();
  const insets = useSafeAreaInsets();
  const { user } = useAuth();

  const [data, setData] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [series, setSeries] = useState<"weight" | "energy" | "pain">("weight");
  const [rightMode, setRightMode] = useState<"render" | "photo">("render");
  const [weight, setWeight] = useState("");
  const [uploading, setUploading] = useState(false);

  const load = useCallback(async () => {
    const [p, l] = await Promise.all([api.get<any>("/progress"), api.get<{ logs: any[] }>("/logs")]);
    setData(p); setLogs(l.logs);
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  const addPhoto = async () => {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) return;
    const res = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.8 });
    if (res.canceled || !res.assets?.[0]) return;
    setUploading(true);
    try {
      await uploadPhoto("/progress/photo", res.assets[0].uri, `progress-${Date.now()}.jpg`);
      await load();
    } finally { setUploading(false); }
  };

  const logWeight = async () => {
    if (!Number(weight)) return;
    await api.post("/logs", { date: new Date().toISOString().slice(0, 10), weight_kg: Number(weight) });
    setWeight("");
    await load();
  };

  if (!data) return <Screen><View style={{ flex: 1 }} /></Screen>;

  const unit = user?.unit_preference || "metric";
  const latestPhoto = data.progress_photos?.[data.progress_photos.length - 1];
  const rightUri = rightMode === "render"
    ? fileUrl(data.chosen_render?.path)
    : fileUrl(latestPhoto?.path);

  const chartData =
    series === "weight"
      ? data.weight_series.map((w: any) => ({ x: w.date.slice(5), y: kgToDisplay(w.weight_kg, unit).value }))
      : logs.filter((l) => l[series] != null).map((l) => ({ x: l.date.slice(5), y: l[series] }));
  const chartUnit = series === "weight" ? kgToDisplay(1, unit).unit : "1–5";

  const firstW = data.weight_series[0]?.weight_kg;
  const lastW = data.weight_series[data.weight_series.length - 1]?.weight_kg;
  const delta = firstW != null && lastW != null ? kgToDisplay(lastW - firstW, unit) : null;

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ paddingTop: insets.top + spacing.md, paddingHorizontal: spacing.lg, paddingBottom: spacing.xl }}>
        <Label>Progress</Label>
        <Text style={{ color: colors.textPrimary, fontSize: font.size.xl, fontWeight: "200", marginBottom: spacing.md }}>Then vs now</Text>

        <View style={{ flexDirection: "row", gap: spacing.sm, marginBottom: spacing.sm }}>
          <Chip testID="progress-right-render" label="vs Target render" active={rightMode === "render"} onPress={() => setRightMode("render")} />
          <Chip testID="progress-right-photo" label="vs Latest photo" active={rightMode === "photo"} onPress={() => setRightMode("photo")} />
        </View>
        <ComparisonViewer
          leftUri={fileUrl(data.base_photo_path)}
          rightUri={rightUri}
          leftLabel="BASE"
          rightLabel={rightMode === "render" ? "TARGET" : "NOW"}
        />
        <Text style={{ color: colors.textTertiary, fontSize: font.size.xs, marginTop: 6 }}>Drag the divider to compare.</Text>

        {data.chosen_render ? (
          <Card testID="progress-render-stats" style={{ marginTop: spacing.md }}>
            <Label>Your chosen target</Label>
            <View style={{ flexDirection: "row", gap: spacing.lg, marginTop: spacing.sm }}>
              <StatReadout value={kgToDisplay(data.chosen_render.weight_kg, unit).value} unit={kgToDisplay(1, unit).unit} label="target weight" size={font.size.xl} />
              <StatReadout value={data.chosen_render.body_fat_pct} unit="%" label="est. body fat" size={font.size.xl} />
            </View>
            <Text style={{ color: colors.textSecondary, fontSize: font.size.sm, marginTop: spacing.sm }}>{data.chosen_render.what_it_takes}</Text>
          </Card>
        ) : null}

        <GradientButton testID="progress-add-photo" label="Add progress photo" icon="camera" loading={uploading} onPress={addPhoto} />

        {/* Weight log */}
        <View style={{ marginTop: spacing.lg }}>
          <Label>Log weight</Label>
          <View style={{ flexDirection: "row", gap: spacing.sm, marginTop: spacing.sm, alignItems: "flex-end" }}>
            <View style={{ flex: 1 }}>
              <TextField testID="progress-weight-input" value={weight} onChangeText={setWeight} placeholder={`Today's weight (${kgToDisplay(1, unit).unit})`} keyboardType="numeric" />
            </View>
            <View style={{ width: 120 }}>
              <GradientButton testID="progress-weight-save" label="Save" onPress={logWeight} />
            </View>
          </View>
        </View>

        {/* Chart */}
        <View style={{ marginTop: spacing.lg }}>
          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
            <Label>Trend</Label>
            {delta ? <StatReadout value={`${delta.value > 0 ? "+" : ""}${delta.value}`} unit={delta.unit} label="net change" align="center" size={font.size.xl} /> : null}
          </View>
          <Card style={{ marginTop: spacing.sm }}>
            <LineChart
              data={chartData}
              unit={chartUnit}
              color={series === "weight" ? [colors.accentTeal, colors.accentBlue] : series === "energy" ? [colors.accentBlue, colors.accentViolet] : [colors.warning, colors.alert]}
            />
            <View style={{ flexDirection: "row", gap: spacing.sm, marginTop: spacing.md }}>
              <Chip testID="chart-weight" label="Weight" active={series === "weight"} onPress={() => setSeries("weight")} />
              <Chip testID="chart-energy" label="Energy" active={series === "energy"} onPress={() => setSeries("energy")} />
              <Chip testID="chart-pain" label="Pain" active={series === "pain"} onPress={() => setSeries("pain")} />
            </View>
          </Card>
        </View>

        <View style={{ marginTop: spacing.md }}><MedicalDisclaimer /></View>
      </ScrollView>
    </Screen>
  );
}

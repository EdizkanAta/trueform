import { useState } from "react";
import { Linking, Platform, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as ImagePicker from "expo-image-picker";
import { Image } from "expo-image";
import Svg, { Path } from "react-native-svg";
import { Feather } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";

import { useTheme } from "@/src/theme/ThemeContext";
import { overlay } from "@/src/theme/theme";
import { useAuth } from "@/src/context/AuthContext";
import { uploadPhoto } from "@/src/api/client";
import { GradientButton, OutlineButton, Label, Screen } from "@/src/components/ui";

// Rough full-body silhouette used as a capture guide overlay.
const SILHOUETTE =
  "M50 8 C56 8 60 13 60 20 C60 27 56 31 50 31 C44 31 40 27 40 20 C40 13 44 8 50 8 Z " +
  "M42 33 L58 33 C64 33 66 40 66 50 L64 92 L56 92 L54 60 L52 60 L52 150 L46 150 L46 92 " +
  "L44 60 L44 150 L38 150 L38 60 L36 92 L34 92 L34 50 C34 40 36 33 42 33 Z";

export default function Photo() {
  const router = useRouter();
  const { colors, spacing, font, radius } = useTheme();
  const insets = useSafeAreaInsets();
  const { refresh } = useAuth();

  const [permission, requestPermission] = useCameraPermissions();
  const [mode, setMode] = useState<"intro" | "camera">("intro");
  const [preview, setPreview] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  let cameraRef: CameraView | null = null;

  const openCamera = async () => {
    setError(null);
    if (!permission?.granted) {
      const res = await requestPermission();
      if (!res.granted) {
        if (!res.canAskAgain) {
          setError("Camera access is blocked. Enable it in Settings to take a photo.");
        }
        return;
      }
    }
    setMode("camera");
  };

  const pickFromGallery = async () => {
    setError(null);
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) {
      if (!perm.canAskAgain) setError("Photo access is blocked. Enable it in Settings.");
      return;
    }
    const res = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"], quality: 0.8, allowsEditing: false,
    });
    if (!res.canceled && res.assets?.[0]) setPreview(res.assets[0].uri);
  };

  const capture = async () => {
    if (!cameraRef) return;
    const shot = await cameraRef.takePictureAsync({ quality: 0.8 });
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    setPreview(shot?.uri ?? null);
    setMode("intro");
  };

  const confirmUpload = async () => {
    if (!preview) return;
    setUploading(true);
    setError(null);
    try {
      await uploadPhoto("/photo/upload", preview, `base-${Date.now()}.jpg`);
      await refresh();
      router.replace("/generating");
    } catch (e: any) {
      setError(e?.message || "Upload failed, please try again.");
    } finally {
      setUploading(false);
    }
  };

  if (mode === "camera") {
    return (
      <View style={{ flex: 1, backgroundColor: overlay.cameraBg }}>
        <CameraView ref={(r) => { cameraRef = r; }} style={{ flex: 1 }} facing="back">
          <View style={{ flex: 1, alignItems: "center", justifyContent: "center" }}>
            <Svg width="55%" height="70%" viewBox="0 0 100 160">
              <Path d={SILHOUETTE} fill="none" stroke={overlay.silhouette} strokeWidth={1} strokeDasharray="3 3" />
            </Svg>
          </View>
          <View style={{ position: "absolute", top: insets.top + 12, left: 0, right: 0, alignItems: "center" }}>
            <Text style={{ color: overlay.onImage, fontSize: font.size.sm, backgroundColor: overlay.scrim, paddingHorizontal: 12, paddingVertical: 6, borderRadius: radius.pill }}>
              Stand back · full body in frame · neutral background
            </Text>
          </View>
          <View style={{ position: "absolute", bottom: insets.bottom + 30, left: 0, right: 0, alignItems: "center", flexDirection: "row", justifyContent: "space-around" }}>
            <Feather name="x" size={28} color={overlay.onImage} onPress={() => setMode("intro")} />
            <Feather name="circle" testID="camera-capture" size={72} color={overlay.onImage} onPress={capture} />
            <View style={{ width: 28 }} />
          </View>
        </CameraView>
      </View>
    );
  }

  return (
    <Screen>
      <View style={{ flex: 1, paddingTop: insets.top + spacing.md, paddingHorizontal: spacing.lg, paddingBottom: insets.bottom + spacing.md }}>
        <Label>Base photo</Label>
        <Text style={{ color: colors.textPrimary, fontSize: font.size.xl, fontWeight: "200", marginTop: 4 }}>
          A guided full-body shot
        </Text>
        <Text style={{ color: colors.textSecondary, marginTop: 6, lineHeight: 20 }}>
          Front pose, arms relaxed, form-fitting clothing, neutral background. This photo stays
          private and is only used to render your realistic targets.
        </Text>

        <View style={{ flex: 1, marginTop: spacing.lg, borderRadius: 16, borderWidth: 1, borderColor: colors.border, overflow: "hidden", backgroundColor: colors.surface, alignItems: "center", justifyContent: "center" }}>
          {preview ? (
            <Image testID="photo-preview" source={{ uri: preview }} style={{ width: "100%", height: "100%" }} contentFit="cover" />
          ) : (
            <Svg width="45%" height="70%" viewBox="0 0 100 160">
              <Path d={SILHOUETTE} fill={colors.surfaceElevated} stroke={colors.border} strokeWidth={1} />
            </Svg>
          )}
        </View>

        {error ? <Text testID="photo-error" style={{ color: colors.alert, marginTop: spacing.sm }}>{error}</Text> : null}

        <View style={{ gap: spacing.sm, marginTop: spacing.md }}>
          {preview ? (
            <>
              <GradientButton testID="photo-confirm" label="Use this photo" icon="check" loading={uploading} onPress={confirmUpload} />
              <OutlineButton testID="photo-retake" label="Choose a different one" onPress={() => setPreview(null)} />
            </>
          ) : (
            <>
              <GradientButton testID="photo-camera" label="Take a photo" icon="camera" onPress={openCamera} />
              <OutlineButton testID="photo-gallery" label="Upload from gallery" onPress={pickFromGallery} />
            </>
          )}
          {error && error.includes("Settings") ? (
            <OutlineButton testID="photo-settings" label="Open Settings" onPress={() => Linking.openSettings()} />
          ) : null}
        </View>
      </View>
    </Screen>
  );
}

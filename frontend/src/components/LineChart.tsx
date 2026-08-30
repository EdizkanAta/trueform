import React from "react";
import { View, Text } from "react-native";
import Svg, { Circle, Defs, LinearGradient, Path, Line, Stop } from "react-native-svg";

import { useTheme } from "@/src/theme/ThemeContext";

type Props = {
  data: { x: string; y: number }[];
  unit: string;
  color?: [string, string];
  height?: number;
};

export function LineChart({ data, unit, color, height = 180 }: Props) {
  const { colors, font } = useTheme();
  const width = 320; // laid out responsively via viewBox scaling
  const padX = 12;
  const padY = 20;
  const c0 = color?.[0] ?? colors.accentTeal;
  const c1 = color?.[1] ?? colors.accentViolet;

  if (data.length < 2) {
    return (
      <View style={{ height, alignItems: "center", justifyContent: "center" }}>
        <Text style={{ color: colors.textTertiary, fontSize: font.size.sm }}>
          Log at least two entries to see the trend.
        </Text>
      </View>
    );
  }

  const ys = data.map((d) => d.y);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const range = maxY - minY || 1;
  const stepX = (width - padX * 2) / (data.length - 1);

  const points = data.map((d, i) => {
    const x = padX + i * stepX;
    const y = padY + (1 - (d.y - minY) / range) * (height - padY * 2);
    return { x, y };
  });

  const path = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(" ");

  const gridLines = [0, 0.25, 0.5, 0.75, 1].map((t) => padY + t * (height - padY * 2));

  return (
    <View>
      <Svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`}>
        <Defs>
          <LinearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
            <Stop offset="0" stopColor={c0} />
            <Stop offset="1" stopColor={c1} />
          </LinearGradient>
        </Defs>
        {gridLines.map((gy, i) => (
          <Line key={i} x1={padX} y1={gy} x2={width - padX} y2={gy}
            stroke={colors.border} strokeWidth={0.5} />
        ))}
        <Path d={path} stroke="url(#lineGrad)" strokeWidth={2} fill="none"
          strokeLinecap="round" strokeLinejoin="round" />
        {points.map((p, i) => (
          <Circle key={i} cx={p.x} cy={p.y} r={3} fill={colors.bg}
            stroke={i === points.length - 1 ? c1 : c0} strokeWidth={2} />
        ))}
      </Svg>
      <View style={{ flexDirection: "row", justifyContent: "space-between", paddingHorizontal: 4, marginTop: 4 }}>
        <Text style={{ color: colors.textTertiary, fontSize: font.size.xs }}>{data[0].x}</Text>
        <Text style={{ color: colors.textTertiary, fontSize: font.size.xs }}>
          {data[data.length - 1].x} · {unit}
        </Text>
      </View>
    </View>
  );
}

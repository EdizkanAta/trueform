// Unit + display formatting helpers.
export const KG_PER_LB = 0.45359237;

export function kgToDisplay(kg: number, unit: string): { value: number; unit: string } {
  if (unit === "imperial") return { value: Math.round((kg / KG_PER_LB) * 10) / 10, unit: "lb" };
  return { value: Math.round(kg * 10) / 10, unit: "kg" };
}

export function cmToDisplay(cm: number, unit: string): string {
  if (unit === "imperial") {
    const inches = cm / 2.54;
    const ft = Math.floor(inches / 12);
    const inch = Math.round(inches - ft * 12);
    return `${ft}'${inch}"`;
  }
  return `${Math.round(cm)} cm`;
}

export const CONDITION_LABELS: Record<string, string> = {
  type2Diabetes: "Type 2 Diabetes",
  prediabetes: "Prediabetes",
  NAFLD: "NAFLD (fatty liver)",
  hypothyroid: "Hypothyroidism",
  hyperthyroid: "Hyperthyroidism",
  PCOS: "PCOS",
  hypertension: "Hypertension",
  highCholesterol: "High Cholesterol",
};

export const ENV_LABELS: Record<string, string> = {
  gym: "Gym",
  home_equipment: "Home + Equipment",
  home_no_equipment: "Home, No Equipment",
};

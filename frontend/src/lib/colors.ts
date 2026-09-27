export function spiColor(spi: number): string {
  if (spi >= 81) return "#0f766e";
  if (spi >= 61) return "#2563eb";
  if (spi >= 41) return "#d97706";
  return "#b91c1c";
}

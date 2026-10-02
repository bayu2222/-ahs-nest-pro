// Deterministic fill color per shape type (technical CAD palette).
const TYPE_COLORS = {
  rectangle: "#38BDF8",
  circle: "#34D399",
  triangle: "#FBBF24",
  polygon: "#A78BFA",
};

export function shapeColor(type) {
  return TYPE_COLORS[type] || "#60A5FA";
}

export function shapeFill(type) {
  const c = shapeColor(type);
  return c + "26"; // ~15% alpha
}

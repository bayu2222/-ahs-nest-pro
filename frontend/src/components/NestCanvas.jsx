import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { shapeColor, shapeFill } from "@/lib/colors";

const MARGIN = { left: 40, top: 22, right: 14, bottom: 26 };

function chooseTick(spanCm) {
  // pick a "nice" ruler step so labels stay readable
  const targets = [1, 2, 5, 10, 20, 25, 50, 100];
  const approx = spanCm / 12;
  return targets.reduce((a, b) => (Math.abs(b - approx) < Math.abs(a - approx) ? b : a), 10);
}

export default function NestCanvas({ result, settings, debug, emptyHint }) {
  const wrapRef = useRef(null);
  const [cw, setCw] = useState(900);

  useLayoutEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      setCw(entries[0].contentRect.width);
    });
    ro.observe(el);
    setCw(el.clientWidth);
    return () => ro.disconnect();
  }, []);

  const mediaW = settings.mediaWidth;
  const stats = result?.stats;
  let Hcm;
  if (settings.heightMode === "fixed") {
    Hcm = settings.mediaHeight || 80;
  } else {
    Hcm = stats ? Math.max(stats.usedHeight, 8) : 60;
  }
  Hcm = Math.max(Hcm, 1);

  const pxPerCm = Math.max((cw - MARGIN.left - MARGIN.right) / mediaW, 0.001);
  const drawW = mediaW * pxPerCm;
  const drawH = Hcm * pxPerCm;
  const svgW = cw;
  const svgH = drawH + MARGIN.top + MARGIN.bottom;

  const X = (xc) => MARGIN.left + xc * pxPerCm;
  const Y = (yc) => MARGIN.top + (Hcm - yc) * pxPerCm; // y=0 at bottom

  const tick = chooseTick(Math.max(mediaW, Hcm));
  const xTicks = [];
  for (let c = 0; c <= mediaW + 1e-6; c += tick) xTicks.push(Math.round(c * 1000) / 1000);
  const yTicks = [];
  for (let c = 0; c <= Hcm + 1e-6; c += tick) yTicks.push(Math.round(c * 1000) / 1000);

  const polyPoints = (pts) => pts.map(([x, y]) => `${X(x)},${Y(y)}`).join(" ");
  const placed = (result?.objects || []).filter((o) => o.placed && o.rotatedPoints);

  const dbg = result?.debug;

  return (
    <div ref={wrapRef} className="w-full" data-testid="nest-canvas">
      <svg width={svgW} height={svgH} style={{ display: "block" }}>
        <defs>
          <pattern id="grid" width={tick * pxPerCm} height={tick * pxPerCm} patternUnits="userSpaceOnUse">
            <path
              d={`M ${tick * pxPerCm} 0 L 0 0 0 ${tick * pxPerCm}`}
              fill="none"
              stroke="#ffffff"
              strokeOpacity="0.06"
              strokeWidth="1"
            />
          </pattern>
        </defs>

        {/* media surface */}
        <rect x={MARGIN.left} y={MARGIN.top} width={drawW} height={drawH} fill="#1A1A1A" />
        <rect
          x={MARGIN.left}
          y={MARGIN.top}
          width={drawW}
          height={drawH}
          fill="url(#grid)"
          transform={`translate(0, ${(drawH % (tick * pxPerCm))})`}
        />
        {/* boundary */}
        <rect
          x={MARGIN.left}
          y={MARGIN.top}
          width={drawW}
          height={drawH}
          fill="none"
          stroke="#007AFF"
          strokeOpacity="0.5"
          strokeWidth="1.5"
        />

        {/* rulers */}
        {xTicks.map((c) => (
          <g key={`xt-${c}`}>
            <line x1={X(c)} y1={MARGIN.top - 5} x2={X(c)} y2={MARGIN.top} stroke="#71717A" strokeWidth="1" />
            <text
              x={X(c)}
              y={MARGIN.top - 8}
              fill="#A1A1AA"
              fontSize="9"
              textAnchor="middle"
              fontFamily="JetBrains Mono, monospace"
            >
              {c}
            </text>
          </g>
        ))}
        {yTicks.map((c) => (
          <g key={`yt-${c}`}>
            <line x1={MARGIN.left - 5} y1={Y(c)} x2={MARGIN.left} y2={Y(c)} stroke="#71717A" strokeWidth="1" />
            <text
              x={MARGIN.left - 7}
              y={Y(c) + 3}
              fill="#A1A1AA"
              fontSize="9"
              textAnchor="end"
              fontFamily="JetBrains Mono, monospace"
            >
              {c}
            </text>
          </g>
        ))}
        <text
          x={MARGIN.left}
          y={svgH - 8}
          fill="#71717A"
          fontSize="9"
          fontFamily="JetBrains Mono, monospace"
        >
          units: cm — origin bottom-left — media {mediaW} × {Hcm.toFixed(1)} cm
        </text>

        {/* debug: rejected positions */}
        {debug.showRejected &&
          dbg?.rejected?.map((r, i) => (
            <rect
              key={`rej-${i}`}
              x={X(r.x)}
              y={Y(r.y + r.height)}
              width={r.width * pxPerCm}
              height={r.height * pxPerCm}
              fill="none"
              stroke="#FF3B30"
              strokeOpacity="0.35"
              strokeWidth="1"
              strokeDasharray="2 2"
            />
          ))}

        {/* debug: candidate positions */}
        {debug.showCandidates &&
          dbg?.candidates?.map((r, i) => (
            <rect
              key={`cand-${i}`}
              x={X(r.x)}
              y={Y(r.y + r.height)}
              width={r.width * pxPerCm}
              height={r.height * pxPerCm}
              fill="none"
              stroke="#007AFF"
              strokeOpacity="0.5"
              strokeWidth="1"
              strokeDasharray="3 2"
            />
          ))}

        {/* placed objects */}
        {placed.map((o) => {
          const cx = (o.bbox.minX + o.bbox.maxX) / 2;
          const cy = (o.bbox.minY + o.bbox.maxY) / 2;
          return (
            <g key={o.id} data-testid={`nested-object-${o.id}`}>
              <polygon
                points={polyPoints(o.rotatedPoints)}
                fill={shapeFill(o.type)}
                stroke={shapeColor(o.type)}
                strokeWidth="1.3"
              />
              {pxPerCm > 2.2 && (
                <text
                  x={X(cx)}
                  y={Y(cy)}
                  fill="#FFFFFF"
                  fontSize={Math.min(11, Math.max(7, pxPerCm * 0.9))}
                  textAnchor="middle"
                  fontFamily="JetBrains Mono, monospace"
                >
                  {o.id.replace("obj-", "#")}
                </text>
              )}
              {pxPerCm > 3.2 && o.rotation !== 0 && (
                <text
                  x={X(cx)}
                  y={Y(cy) + 11}
                  fill="#A1A1AA"
                  fontSize="8"
                  textAnchor="middle"
                  fontFamily="JetBrains Mono, monospace"
                >
                  {o.rotation}°
                </text>
              )}
            </g>
          );
        })}

        {/* debug: bounding boxes */}
        {debug.showBBox &&
          placed.map((o) => (
            <rect
              key={`bb-${o.id}`}
              x={X(o.bbox.minX)}
              y={Y(o.bbox.maxY)}
              width={(o.bbox.maxX - o.bbox.minX) * pxPerCm}
              height={(o.bbox.maxY - o.bbox.minY) * pxPerCm}
              fill="none"
              stroke="#FF00FF"
              strokeWidth="1"
              strokeDasharray="4 2"
            />
          ))}

        {/* debug: collision areas */}
        {debug.showCollisions &&
          dbg?.collisions?.map((c, i) => (
            <polygon
              key={`col-${i}`}
              points={polyPoints(c.points)}
              fill="#FF3B30"
              fillOpacity="0.4"
              stroke="#FF3B30"
              strokeWidth="1"
            />
          ))}
      </svg>

      {!result && (
        <div className="mt-3 text-sm text-[#71717A] font-mono-data" data-testid="canvas-empty-hint">
          {emptyHint}
        </div>
      )}
    </div>
  );
}

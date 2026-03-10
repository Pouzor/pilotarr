import React from "react";

/**
 * Pilotarr brand icon — radar/navigator theme.
 * Uses unique gradient IDs scoped per instance to avoid SVG conflicts.
 */
const PilotarrLogo = ({ size = 32, className = "" }) => {
  const uid = React.useId().replace(/:/g, "");

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 64 64"
      className={className}
      aria-label="Pilotarr logo"
    >
      <defs>
        <linearGradient id={`grad-${uid}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#3b82f6" />
          <stop offset="100%" stopColor="#6366f1" />
        </linearGradient>
        <radialGradient id={`sweep-${uid}`} cx="65%" cy="30%" r="70%">
          <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.45" />
          <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* Background */}
      <rect width="64" height="64" rx="14" fill="#0f172a" />

      {/* Radar rings */}
      <circle
        cx="32"
        cy="32"
        r="24"
        fill="none"
        stroke={`url(#grad-${uid})`}
        strokeWidth="1.5"
        opacity="0.35"
      />
      <circle
        cx="32"
        cy="32"
        r="14"
        fill="none"
        stroke={`url(#grad-${uid})`}
        strokeWidth="1"
        opacity="0.25"
      />

      {/* Crosshairs */}
      <line x1="32" y1="8" x2="32" y2="56" stroke="#3b82f6" strokeWidth="0.75" opacity="0.12" />
      <line x1="8" y1="32" x2="56" y2="32" stroke="#3b82f6" strokeWidth="0.75" opacity="0.12" />

      {/* Sweep sector (270° → 315°) */}
      <path d="M32,32 L32,8 A24,24 0 0,1 49,15 Z" fill={`url(#sweep-${uid})`} />

      {/* Sweep arm */}
      <line
        x1="32"
        y1="32"
        x2="49"
        y2="15"
        stroke={`url(#grad-${uid})`}
        strokeWidth="2"
        strokeLinecap="round"
        opacity="0.9"
      />

      {/* Blip */}
      <circle cx="44" cy="19" r="3.5" fill="#f59e0b" />
      <circle cx="44" cy="19" r="6" fill="none" stroke="#f59e0b" strokeWidth="1" opacity="0.4" />

      {/* Center dot */}
      <circle cx="32" cy="32" r="2.5" fill={`url(#grad-${uid})`} />
    </svg>
  );
};

export default PilotarrLogo;

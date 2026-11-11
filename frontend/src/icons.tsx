import React from 'react';

const base = {
  width: 18,
  height: 18,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
};

export const FlagIcon = () => (
  <svg {...base} width={24} height={24}>
    <path d="M4 22V4M4 4h13l-2 4 2 4H4" />
  </svg>
);
export const PenIcon = () => (
  <svg {...base}>
    <path d="M12 20h9M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4z" />
  </svg>
);
export const RectIcon = () => (
  <svg {...base}>
    <rect x="4" y="5" width="16" height="14" />
  </svg>
);
export const TextIcon = () => (
  <svg {...base}>
    <path d="M5 6V4h14v2M12 4v16M9 20h6" />
  </svg>
);
export const UndoIcon = () => (
  <svg {...base}>
    <path d="M3 7v6h6M3 13a9 9 0 119 8" />
  </svg>
);
export const TrashIcon = () => (
  <svg {...base}>
    <path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14" />
  </svg>
);

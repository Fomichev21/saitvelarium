function svg(inner, size = 16) {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="${size}" height="${size}">${inner}</svg>`;
}

export const ICON_COPY = svg('<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>');
export const ICON_QR = svg(
  '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><path d="M14 14h3v3h-3zM19 14h2v2h-2zM14 19h2v2h-2zM19 19h2v2h-2z"/>',
  18
);
export const ICON_SMARTPHONE = svg('<rect x="6" y="2" width="12" height="20" rx="2"/><path d="M10 18h4"/>');
export const ICON_ARROW_OUT = svg('<path d="M7 17 17 7M9 7h8v8"/>');
export const ICON_SEND = svg('<path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4z"/>');
export const ICON_HEADSET = svg(
  '<path d="M4 13a8 8 0 0 1 16 0"/><rect x="3" y="13" width="4" height="7" rx="1.5"/><rect x="17" y="13" width="4" height="7" rx="1.5"/><path d="M20 20a4 4 0 0 1-4 3h-2"/>'
);
export const ICON_DOWNLOAD = svg('<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/>');
export const ICON_PLUS = svg('<path d="M12 5v14M5 12h14"/>');
export const ICON_EDIT = svg('<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>', 14);
export const ICON_TRASH = svg('<path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>', 14);
export const ICON_BAN = svg('<circle cx="12" cy="12" r="9"/><path d="m5 5 14 14"/>');
export const ICON_CHECK = svg('<path d="M20 6 9 17l-5-5"/>');
export const ICON_X = svg('<path d="M18 6 6 18M6 6l12 12"/>', 14);
export const ICON_WALLET_LG = svg(
  '<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18"/><circle cx="16" cy="14.5" r="1"/>',
  18
);
export const ICON_RECEIPT = svg(
  '<path d="M6 2h12v20l-3-2-3 2-3-2-3 2V2Z"/><path d="M9 8h6M9 12h6"/>',
  18
);
export const ICON_CALENDAR = svg(
  '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>',
  18
);
export const ICON_MINUS = svg('<path d="M5 12h14"/>');
export const ICON_CLOCK = svg('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/>', 14);
export const ICON_WALLET = svg(
  '<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18"/><circle cx="16" cy="14.5" r="1"/>',
  14
);
export const ICON_MEGAPHONE = svg('<path d="M3 10v4h3l7 4V6l-7 4H3z"/><path d="M17 9a4 4 0 0 1 0 6"/>');
export const ICON_SAVE = svg(
  '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z"/><path d="M17 21v-8H7v8"/><path d="M7 3v5h8"/>'
);
export const ICON_BOLT = svg('<path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z"/>', 15);
export const ICON_GLOBE = svg(
  '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3c2.5 2.5 4 5.7 4 9s-1.5 6.5-4 9c-2.5-2.5-4-5.7-4-9s1.5-6.5 4-9Z"/>',
  15
);
export const ICON_LOCK = svg('<rect x="4" y="10" width="16" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>', 15);
export const ICON_DEVICES = svg(
  '<rect x="3" y="4" width="14" height="10" rx="1.5"/><path d="M8 20h6"/><path d="M11 14v6"/><rect x="17" y="9" width="5" height="8" rx="1"/>',
  15
);

export const HIGHLIGHT_ICONS = {
  bolt: ICON_BOLT,
  globe: ICON_GLOBE,
  lock: ICON_LOCK,
  devices: ICON_DEVICES,
};

export function LogoMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <defs>
        <linearGradient id="sr-logo" x1="4" y1="2" x2="28" y2="30" gradientUnits="userSpaceOnUse">
          <stop stopColor="#a494ff" />
          <stop offset="1" stopColor="#5f9dff" />
        </linearGradient>
      </defs>
      <path d="M16 1.8 28.3 8.9v14.2L16 30.2 3.7 23.1V8.9L16 1.8Z" fill="url(#sr-logo)" />
      <path d="M16 1.8 28.3 8.9v14.2L16 30.2 3.7 23.1V8.9L16 1.8Z" fill="none" stroke="#fff" strokeOpacity=".25" />
      <path d="M11 9.5h10v13.2l-5-3.2-5 3.2V9.5Z" fill="#0e0a24" fillOpacity=".85" />
      <path d="m16.9 11.6-3 4.4h2.6l-1.2 3.9 3.3-4.9h-2.6l.9-3.4Z" fill="#f6c35b" />
    </svg>
  );
}

export function Logo() {
  return (
    <span className="inline-flex items-center gap-2.5">
      <LogoMark />
      <span className="font-display text-[17px] font-bold tracking-tight">StudyRaid</span>
    </span>
  );
}

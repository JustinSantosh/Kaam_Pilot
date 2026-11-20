/** The KaamPilot mark: a chat bubble sending the quote off as a paper plane (D-027). */
export function LogoMark({ size = 36, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      aria-hidden="true"
      className={`shrink-0 ${className}`}
    >
      <path
        d="M12 4H36A9 9 0 0 1 45 13V27A9 9 0 0 1 36 36H20L10 44L12 36A9 9 0 0 1 3 27V13A9 9 0 0 1 12 4Z"
        fill="#FFB81C"
        stroke="#1E1240"
        strokeWidth="2.6"
        strokeLinejoin="round"
      />
      <path
        d="M13.2 17.9L35.2 10.2L23.1 22.3Z"
        fill="#FFFFFF"
        stroke="#1E1240"
        strokeWidth="2.2"
        strokeLinejoin="round"
      />
      <path
        d="M23.1 22.3L35.2 10.2L27.5 32.2Z"
        fill="#FF4D94"
        stroke="#1E1240"
        strokeWidth="2.2"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Lowercase wordmark; in running text the name is still written "KaamPilot". */
export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`font-display font-extrabold leading-none tracking-[-0.045em] text-ink ${className}`}>
      kaam<span className="text-rani">pilot</span>
    </span>
  );
}

/** Stroke icons drawn on a 24px grid: 2px strokes with round ends, coloured by `currentColor`. */

import type { ReactNode, SVGProps } from "react";

type IconProps = Omit<SVGProps<SVGSVGElement>, "children"> & { size?: number };

function Icon({ size = 18, strokeWidth = 2, children, ...props }: IconProps & { children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  );
}

export const SendIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M21.5 2.5 10.5 13.5" />
    <path d="M21.5 2.5 14.5 21.5 10.5 13.5 2.5 9.5Z" />
  </Icon>
);

export const MicIcon = (p: IconProps) => (
  <Icon {...p}>
    <rect x="9" y="2.5" width="6" height="12" rx="3" />
    <path d="M5 11a7 7 0 0 0 14 0" />
    <path d="M12 18v3.5" />
  </Icon>
);

export const CheckIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M4.5 12.5 9.5 17.5 19.5 6.5" />
  </Icon>
);

export const CloseIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M6 6 18 18M18 6 6 18" />
  </Icon>
);

export const PencilIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M4 20h4.5L19.5 9a2.12 2.12 0 0 0-3-3L5.5 17Z" />
    <path d="m14.5 8 3 3" />
  </Icon>
);

export const FileIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M14 2.5H7A2 2 0 0 0 5 4.5v15a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7.5Z" />
    <path d="M14 2.5v5h5" />
    <path d="M9 13h6M9 17h4" />
  </Icon>
);

export const DownloadIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M12 3.5v11" />
    <path d="m7 10 5 5 5-5" />
    <path d="M4.5 20.5h15" />
  </Icon>
);

export const ClockIcon = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v5l3.5 2" />
  </Icon>
);

export const AlertIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M10.3 4.2 2.6 18a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0Z" />
    <path d="M12 9.5v4" />
    <path d="M12 17.2h.01" />
  </Icon>
);

export const UserIcon = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="12" cy="8" r="4" />
    <path d="M4.5 21a7.5 7.5 0 0 1 15 0" />
  </Icon>
);

export const PlusIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M12 5v14M5 12h14" />
  </Icon>
);

export const ArrowRightIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M4.5 12h15" />
    <path d="m13 5.5 6.5 6.5-6.5 6.5" />
  </Icon>
);

export const ChatIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M20.5 11.5a8.5 8.5 0 0 1-12.4 7.6L3.5 20.5l1.4-4.4a8.5 8.5 0 1 1 15.6-4.6Z" />
  </Icon>
);

export const InboxIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M3 13.5h5l1.5 3h5l1.5-3h5" />
    <path d="M5.5 5h13l2.5 8.5V19a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 19v-5.5Z" />
  </Icon>
);

export const StoreIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M3.5 9.5 5 4h14l1.5 5.5" />
    <path d="M3.5 9.5a2.83 2.83 0 0 0 5.67 0 2.83 2.83 0 0 0 5.66 0 2.83 2.83 0 0 0 5.67 0" />
    <path d="M5 12v8.5h14V12" />
    <path d="M10 20.5v-5h4v5" />
  </Icon>
);

export const LogoutIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M14.5 4.5h4a1.5 1.5 0 0 1 1.5 1.5v12a1.5 1.5 0 0 1-1.5 1.5h-4" />
    <path d="M9.5 8 5.5 12l4 4" />
    <path d="M5.5 12h10" />
  </Icon>
);

export const RefreshIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M20 11a8 8 0 0 0-14.5-4.5L4 8" />
    <path d="M4 3.5V8h4.5" />
    <path d="M4 13a8 8 0 0 0 14.5 4.5L20 16" />
    <path d="M20 20.5V16h-4.5" />
  </Icon>
);

export const EyeIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z" />
    <circle cx="12" cy="12" r="3" />
  </Icon>
);

export const CalculatorIcon = (p: IconProps) => (
  <Icon {...p}>
    <rect x="5" y="2.5" width="14" height="19" rx="2.5" />
    <path d="M8.5 7h7" />
    <path d="M8.5 11.5h.01M12 11.5h.01M15.5 11.5h.01M8.5 15h.01M12 15h.01M15.5 15h.01M8.5 18.5h.01M12 18.5h.01M15.5 18.5h.01" />
  </Icon>
);

export const CheckCircleIcon = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="m8 12.2 2.8 2.8 5.2-5.6" />
  </Icon>
);

export const StopIcon = (p: IconProps) => (
  <Icon {...p}>
    <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" />
  </Icon>
);

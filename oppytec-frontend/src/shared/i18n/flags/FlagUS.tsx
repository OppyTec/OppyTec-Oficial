import type { SVGProps } from "react";

export type FlagIconProps = SVGProps<SVGSVGElement> & {
  readonly title?: string;
};

/**
 * Crisp vector SVG flag for English (United States) — `en`.
 */
export function FlagUS({
  title = "English (US)",
  className = "h-4 w-6 rounded-[2px] shadow-sm",
  ...props
}: FlagIconProps) {
  return (
    <svg
      viewBox="0 0 24 16"
      role="img"
      aria-label={title}
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      {...props}
    >
      <title>{title}</title>
      <rect width="24" height="16" fill="#B22234" rx="1.5" />
      <path
        d="M0 2.46h24M0 4.92h24M0 7.38h24M0 9.85h24M0 12.31h24M0 14.77h24"
        stroke="#FFFFFF"
        strokeWidth="1.23"
      />
      <rect width="10.5" height="8.62" fill="#3C3B6E" rx="1" />
      <g fill="#FFFFFF">
        <circle cx="2" cy="1.8" r="0.55" />
        <circle cx="4.2" cy="1.8" r="0.55" />
        <circle cx="6.4" cy="1.8" r="0.55" />
        <circle cx="8.6" cy="1.8" r="0.55" />
        <circle cx="3.1" cy="3.4" r="0.55" />
        <circle cx="5.3" cy="3.4" r="0.55" />
        <circle cx="7.5" cy="3.4" r="0.55" />
        <circle cx="2" cy="5.0" r="0.55" />
        <circle cx="4.2" cy="5.0" r="0.55" />
        <circle cx="6.4" cy="5.0" r="0.55" />
        <circle cx="8.6" cy="5.0" r="0.55" />
        <circle cx="3.1" cy="6.6" r="0.55" />
        <circle cx="5.3" cy="6.6" r="0.55" />
        <circle cx="7.5" cy="6.6" r="0.55" />
      </g>
    </svg>
  );
}

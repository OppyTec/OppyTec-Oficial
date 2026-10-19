import type { FlagIconProps } from "./FlagUS";

/**
 * Crisp vector SVG flag for Español (`es`).
 */
export function FlagES({
  title = "Español",
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
      <rect width="24" height="16" fill="#AA151B" rx="1.5" />
      <rect y="4" width="24" height="8" fill="#F1BF00" />
      <rect x="5" y="5.6" width="2.6" height="4.8" rx="0.8" fill="#AA151B" />
      <circle cx="6.3" cy="8" r="0.75" fill="#F1BF00" />
    </svg>
  );
}

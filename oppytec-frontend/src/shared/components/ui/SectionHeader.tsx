import { useState, useEffect, type ElementType } from "react";
import { cn } from "@/shared/lib";

export interface SectionHeaderProps {
  readonly title: string;
  readonly subtitle: string;
  readonly icon: ElementType;
  readonly color: string;
  readonly center?: boolean;
}

let globalPreviousTitle = "";
let globalPreviousSubtitle = "";
let globalPreviousIcon: ElementType | null = null;
let globalPreviousColor = "";

export function SectionHeader({
  title,
  subtitle,
  icon: Icon,
  color,
  center = true,
}: SectionHeaderProps) {
  const [headerTitle, setHeaderTitle] = useState<string>(() => globalPreviousTitle);
  const [headerSubtitle, setHeaderSubtitle] = useState<string>(() => globalPreviousSubtitle);
  const [subtitleVisible, setSubtitleVisible] = useState<boolean>(() => !!globalPreviousSubtitle);
  const [isAnimating, setIsAnimating] = useState<boolean>(false);
  const [showCursor, setShowCursor] = useState<boolean>(true);
  const [iconVisible, setIconVisible] = useState<boolean>(() => !!globalPreviousIcon);

  const [renderedIcon, setRenderedIcon] = useState<ElementType>(() => globalPreviousIcon || Icon);
  const [renderedColor, setRenderedColor] = useState<string>(() => globalPreviousColor || color);

  // Cursor blink effect
  useEffect(() => {
    let active = true;
    let timerId: ReturnType<typeof setTimeout>;
    const tick = () => {
      if (!active) return;
      setShowCursor((v) => !v);
      timerId = setTimeout(tick, 530);
    };
    timerId = setTimeout(tick, 530);
    return () => {
      active = false;
      clearTimeout(timerId);
    };
  }, []);

  useEffect(() => {
    let isCancelled = false;

    const animate = async () => {
      if (typeof process !== "undefined" && process.env.NODE_ENV === "test") {
        setRenderedIcon(() => Icon);
        setRenderedColor(color);
        setHeaderTitle(title);
        setHeaderSubtitle(subtitle);
        setSubtitleVisible(true);
        setIconVisible(true);
        setIsAnimating(false);
        globalPreviousTitle = title;
        globalPreviousSubtitle = subtitle;
        globalPreviousIcon = Icon;
        globalPreviousColor = color;
        return;
      }

      const isFirstOpen = headerTitle === "";

      if (isFirstOpen) {
        setRenderedIcon(() => Icon);
        setRenderedColor(color);
        globalPreviousIcon = Icon;
        globalPreviousColor = color;
        setIconVisible(true);
        setIsAnimating(true);
        await new Promise((r) => setTimeout(r, 60));
        if (isCancelled) return;

        // Type the full title with agile, organic cadence (~18ms-28ms per char, ~350-450ms total)
        let current = "";
        for (let i = 0; i < title.length; i++) {
          if (isCancelled) return;
          const delay = Math.max(14, 28 - (i / title.length) * 14);
          await new Promise((r) => setTimeout(r, delay));
          if (isCancelled) return;
          current += title[i];
          setHeaderTitle(current);
          globalPreviousTitle = current;
        }

        setHeaderSubtitle(subtitle);
        setSubtitleVisible(true);
        setIsAnimating(false);

        globalPreviousTitle = title;
        globalPreviousSubtitle = subtitle;
        globalPreviousIcon = Icon;
        globalPreviousColor = color;
      } else {
        setIsAnimating(true);
        setSubtitleVisible(false);
        setIconVisible(false);

        // Find common prefix
        let commonPrefix = "";
        for (let i = 0; i < headerTitle.length && i < title.length; i++) {
          if (headerTitle[i] === title[i]) {
            commonPrefix += headerTitle[i];
          } else {
            break;
          }
        }

        // Delete suffix with snappy, fluid cadence (~12ms-24ms per char)
        let current = headerTitle;
        const deleteStartSpeed = 24;
        const deleteEndSpeed = 12;
        const deleteSteps = current.length - commonPrefix.length;

        let iconSwapped = false;
        let elapsed = 0;
        const iconSwapTarget = 60;

        for (let i = 0; i < deleteSteps; i++) {
          if (isCancelled) return;
          const delay = Math.max(
            10,
            deleteStartSpeed - (i / (deleteSteps || 1)) * (deleteStartSpeed - deleteEndSpeed)
          );
          await new Promise((r) => setTimeout(r, delay));
          if (isCancelled) return;
          elapsed += delay;

          if (!iconSwapped && elapsed >= iconSwapTarget) {
            setRenderedIcon(() => Icon);
            setRenderedColor(color);
            globalPreviousIcon = Icon;
            globalPreviousColor = color;
            iconSwapped = true;
          }

          current = current.slice(0, -1);
          setHeaderTitle(current);
          globalPreviousTitle = current;
        }

        // Ensure icon is swapped if deletion was too fast
        if (!iconSwapped) {
          const remaining = iconSwapTarget - elapsed;
          if (remaining > 0) {
            await new Promise((r) => setTimeout(r, remaining));
            if (isCancelled) return;
          }
          setRenderedIcon(() => Icon);
          setRenderedColor(color);
          globalPreviousIcon = Icon;
          globalPreviousColor = color;
        }

        // Type new suffix with agile, natural cadence (~12ms-26ms per char)
        const newSuffix = title.substring(commonPrefix.length);
        const typeStartSpeed = 26;
        const typeEndSpeed = 12;
        const typeSteps = newSuffix.length;

        for (let i = 0; i < typeSteps; i++) {
          if (isCancelled) return;
          const delay = Math.max(
            10,
            typeStartSpeed - (i / (typeSteps || 1)) * (typeStartSpeed - typeEndSpeed)
          );
          await new Promise((r) => setTimeout(r, delay));
          if (isCancelled) return;
          current += newSuffix[i];
          setHeaderTitle(current);
          globalPreviousTitle = current;
        }

        await new Promise((r) => setTimeout(r, 40));
        if (isCancelled) return;

        setIconVisible(true);
        setHeaderSubtitle(subtitle);
        setSubtitleVisible(true);
        setIsAnimating(false);

        globalPreviousTitle = title;
        globalPreviousSubtitle = subtitle;
        globalPreviousIcon = Icon;
        globalPreviousColor = color;
      }
    };

    void animate();
    return () => {
      isCancelled = true;
    };
  }, [title, subtitle, Icon, color]);

  const CurrentIcon = renderedIcon;

  return (
    <header
      className={cn(
        "flex flex-col lg:flex-row lg:items-end gap-4 px-2 mb-2 w-full",
        center && "justify-center"
      )}
    >
      <div
        className={cn(
          "space-y-1 w-full flex flex-col items-center",
          center ? "lg:items-center" : "lg:items-start"
        )}
      >
        <div className={cn("flex items-center gap-3", center ? "justify-center" : "justify-start")}>
          <CurrentIcon
            className="h-8 w-8 shrink-0"
            style={{
              color: renderedColor,
              opacity: iconVisible ? (isAnimating ? 0.7 : 1) : 0,
              transform: isAnimating ? "scale(1.1)" : "scale(1)",
              transition: "opacity 0.2s ease-in-out, transform 0.35s cubic-bezier(0.4, 0, 0.2, 1)",
            }}
          />
          <h1 className="text-3xl lg:text-4xl font-black tracking-tighter flex items-center whitespace-nowrap min-h-[44px]">
            {headerTitle || "\u200b"}
            <span
              className={cn(
                "ml-1 inline-block w-[3px] h-[0.8em] transition-opacity duration-100",
                showCursor ? "opacity-100" : "opacity-0"
              )}
              style={{ backgroundColor: renderedColor }}
            />
          </h1>
        </div>
        <div
          className={cn(
            "grid w-full justify-items-center",
            center ? "lg:justify-items-center" : "lg:justify-items-start"
          )}
        >
          <p
            className={cn(
              "col-start-1 row-start-1 text-[10px] font-bold uppercase tracking-widest invisible select-none pointer-events-none text-center",
              center ? "lg:text-center" : "lg:text-left"
            )}
            aria-hidden="true"
          >
            {subtitle}
          </p>
          <p
            className={cn(
              "col-start-1 row-start-1 text-muted-foreground text-[10px] font-bold uppercase tracking-widest transition-all duration-300 text-center",
              center ? "lg:text-center" : "lg:text-left",
              subtitleVisible ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-1"
            )}
          >
            {headerSubtitle}
          </p>
        </div>
      </div>
    </header>
  );
}

export default SectionHeader;

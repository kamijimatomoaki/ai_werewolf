import { FC, useState, useEffect } from "react";
import clsx from "clsx";

import { SunFilledIcon, MoonFilledIcon } from "@/components/icons";

export interface ThemeSwitchProps {
  className?: string;
}

export const ThemeSwitch: FC<ThemeSwitchProps> = ({
  className,
}) => {
  const [isMounted, setIsMounted] = useState(false);
  const [theme, setTheme] = useState<string>("dark");

  useEffect(() => {
    // Get theme from localStorage or default to dark
    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);
    document.documentElement.className = savedTheme;
    setIsMounted(true);
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === "light" ? "dark" : "light";
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    document.documentElement.className = newTheme;
  };

  // Prevent Hydration Mismatch
  if (!isMounted) return <div className="w-6 h-6" />;

  const isLight = theme === "light";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isLight ? "Switch to dark mode" : "Switch to light mode"}
      className={clsx(
        "p-2 rounded-lg transition-all duration-200 hover:opacity-80 cursor-pointer",
        "bg-transparent text-gray-400 hover:text-white",
        className,
      )}
    >
      <div className="w-auto h-auto bg-transparent rounded-lg flex items-center justify-center">
        {isLight ? (
          <MoonFilledIcon size={22} />
        ) : (
          <SunFilledIcon size={22} />
        )}
      </div>
    </button>
  );
};

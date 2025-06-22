import { PlayerProvider } from "@/contexts/PlayerContext";

export function Provider({ children }: { children: React.ReactNode }) {
  return (
    <div className="dark text-foreground bg-background">
      <PlayerProvider>
        {children}
      </PlayerProvider>
    </div>
  );
}

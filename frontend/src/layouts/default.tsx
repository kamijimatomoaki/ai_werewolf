import { Navbar } from "@/components/navbar";

export default function DefaultLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="relative flex flex-col h-screen">
      <Navbar />
      <main className="container mx-auto max-w-7xl px-6 flex-grow pt-16">
        {children}
      </main>
      <footer className="w-full flex items-center justify-center py-3">
        <a
          className="flex items-center gap-1 text-gray-400 hover:text-gray-300"
          href="https://github.com/anthropics/claude-code"
          target="_blank"
          rel="noopener noreferrer"
          title="Claude Code"
        >
          <span className="text-gray-400">Powered by</span>
          <p className="text-blue-400">Claude Code</p>
        </a>
      </footer>
    </div>
  );
}

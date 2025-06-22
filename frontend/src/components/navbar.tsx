import { useState } from "react";
import clsx from "clsx";

import { siteConfig } from "@/config/site";
import { ThemeSwitch } from "@/components/theme-switch";
import {
  TwitterIcon,
  GithubIcon,
  DiscordIcon,
  HeartFilledIcon,
  SearchIcon,
  Logo,
} from "@/components/icons";

export const Navbar = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const searchInput = (
    <div className="relative">
      <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
      <input
        aria-label="Search"
        className="w-full pl-10 pr-4 py-2 text-sm bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
        placeholder="Search..."
        type="search"
      />
    </div>
  );

  return (
    <nav className="fixed top-0 inset-x-0 z-40 bg-gray-900/90 backdrop-blur-md border-b border-gray-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo and Brand */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Logo />
              <p className="font-bold text-xl text-white">ACME</p>
            </div>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-6">
            {siteConfig.navItems.map((item) => (
              <a
                key={item.href}
                className={clsx(
                  "text-sm font-medium transition-colors hover:text-blue-400",
                  "text-gray-300"
                )}
                href={item.href}
              >
                {item.label}
              </a>
            ))}
          </div>

          {/* Search and Actions */}
          <div className="hidden md:flex items-center gap-4">
            <div className="w-64">
              {searchInput}
            </div>
            <div className="flex items-center gap-2">
              <a
                className="p-2 text-gray-400 hover:text-white transition-colors"
                href={siteConfig.links.github}
                target="_blank"
                rel="noopener noreferrer"
              >
                <GithubIcon className="w-5 h-5" />
              </a>
              <a
                className="p-2 text-gray-400 hover:text-white transition-colors"
                href={siteConfig.links.twitter}
                target="_blank"
                rel="noopener noreferrer"
              >
                <TwitterIcon className="w-5 h-5" />
              </a>
              <a
                className="p-2 text-gray-400 hover:text-white transition-colors"
                href={siteConfig.links.discord}
                target="_blank"
                rel="noopener noreferrer"
              >
                <DiscordIcon className="w-5 h-5" />
              </a>
              <a
                className="inline-flex items-center gap-2 px-3 py-1.5 text-sm bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                href={siteConfig.links.sponsor}
                target="_blank"
                rel="noopener noreferrer"
              >
                <HeartFilledIcon className="w-4 h-4" />
                Sponsor
              </a>
              <ThemeSwitch />
            </div>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              className="p-2 text-gray-400 hover:text-white transition-colors"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {isMenuOpen && (
          <div className="md:hidden py-4 border-t border-gray-700">
            <div className="flex flex-col gap-4">
              <div className="px-2">
                {searchInput}
              </div>
              {siteConfig.navItems.map((item) => (
                <a
                  key={item.href}
                  className="px-2 py-2 text-sm font-medium text-gray-300 hover:text-blue-400 transition-colors"
                  href={item.href}
                  onClick={() => setIsMenuOpen(false)}
                >
                  {item.label}
                </a>
              ))}
              <div className="flex items-center gap-2 px-2 pt-2 border-t border-gray-700">
                <a
                  className="p-2 text-gray-400 hover:text-white transition-colors"
                  href={siteConfig.links.github}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <GithubIcon className="w-5 h-5" />
                </a>
                <a
                  className="p-2 text-gray-400 hover:text-white transition-colors"
                  href={siteConfig.links.twitter}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <TwitterIcon className="w-5 h-5" />
                </a>
                <a
                  className="p-2 text-gray-400 hover:text-white transition-colors"
                  href={siteConfig.links.discord}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <DiscordIcon className="w-5 h-5" />
                </a>
                <a
                  className="inline-flex items-center gap-2 px-3 py-1.5 text-sm bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                  href={siteConfig.links.sponsor}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <HeartFilledIcon className="w-4 h-4" />
                  Sponsor
                </a>
                <ThemeSwitch />
              </div>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
};
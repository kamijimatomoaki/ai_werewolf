import { siteConfig } from "@/config/site";
import { title, subtitle } from "@/components/primitives";
import { GithubIcon } from "@/components/icons";
import DefaultLayout from "@/layouts/default";

export default function IndexPage() {
  return (
    <DefaultLayout>
      <section className="flex flex-col items-center justify-center gap-4 py-8 md:py-10">
        <div className="inline-block max-w-lg text-center justify-center">
          <span className={title()}>Make&nbsp;</span>
          <span className={title({ color: "violet" })}>beautiful&nbsp;</span>
          <br />
          <span className={title()}>
            websites regardless of your design experience.
          </span>
          <div className={subtitle({ class: "mt-4" })}>
            Beautiful, fast and modern React UI library.
          </div>
        </div>

        <div className="flex gap-3">
          <a
            href={siteConfig.links.docs}
            target="_blank"
            rel="noopener noreferrer"
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg transition-colors"
          >
            Documentation
          </a>
          <a
            href={siteConfig.links.github}
            target="_blank"
            rel="noopener noreferrer"
            className="px-6 py-3 border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-full transition-colors flex items-center gap-2"
          >
            <GithubIcon size={20} />
            GitHub
          </a>
        </div>

        <div className="mt-8">
          <div className="p-4 border border-gray-300 rounded-lg bg-gray-50">
            <span>
              Get started by editing{" "}
              <code className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm font-mono">pages/index.tsx</code>
            </span>
          </div>
        </div>
      </section>
    </DefaultLayout>
  );
}

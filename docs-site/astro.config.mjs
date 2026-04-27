// Astro Starlight configuration for ai-engineering docs
// Run `pnpm install` (or `bun install` once Bun supports the Astro toolchain
// fully) inside `docs-site/` before `astro dev`.
import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";

export default defineConfig({
  site: "https://ai-engineering.dev",
  integrations: [
    starlight({
      title: "ai-engineering",
      description:
        "Multi-IDE AI agentic governance framework with subscription piggyback, federated plugins, and dual-plane security.",
      logo: { src: "./public/logo.svg", replacesTitle: false },
      social: {
        github: "https://github.com/soydachi/ai-engineering",
      },
      editLink: {
        baseUrl:
          "https://github.com/soydachi/ai-engineering/edit/main/docs-site/",
      },
      lastUpdated: true,
      pagination: true,
      sidebar: [
        { label: "Get started", autogenerate: { directory: "quickstart" } },
        { label: "Architecture", autogenerate: { directory: "architecture" } },
        { label: "ADRs", autogenerate: { directory: "adr" } },
        { label: "Skills", autogenerate: { directory: "skills" } },
        { label: "Agents", autogenerate: { directory: "agents" } },
      ],
      customCss: ["./src/styles/custom.css"],
    }),
  ],
});

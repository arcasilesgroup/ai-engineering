// Ambient declarations for Bun's `with { type: "file" }` asset imports (blueprint 07:
// the binary is the payload). Each upstream non-TS extension gets a string default.
declare module "*.md" {
  const content: string;
  export default content;
}
// Bun's `with { type: "file" }` returns the module SOURCE as a string. The only
// .ts we embed this way is the generated chain bundle (a real module for plugin
// hosts, but an asset for the binary); tsc otherwise resolves it as a module and
// types the import as the export object, not the file text.
declare module "*.ts" {
  const content: string;
  export default content;
}
declare module "*.json" {
  const content: string;
  export default content;
}
declare module "*.toml" {
  const content: string;
  export default content;
}
declare module "*.mjs" {
  const content: string;
  export default content;
}
declare module "*.cjs" {
  const content: string;
  export default content;
}
declare module "*.py" {
  const content: string;
  export default content;
}
declare module "*.yml" {
  const content: string;
  export default content;
}
declare module "*.yaml" {
  const content: string;
  export default content;
}
declare module "*.html" {
  const content: string;
  export default content;
}
declare module "*.tpl" {
  const content: string;
  export default content;
}
declare module "*.sh" {
  const content: string;
  export default content;
}
// Generated copies of fixture .ts/.tsx data (scripts/gen-assets.ts): an asset the
// binary carries verbatim, with an extension tsc does not resolve as a module.
declare module "*.txt" {
  const content: string;
  export default content;
}

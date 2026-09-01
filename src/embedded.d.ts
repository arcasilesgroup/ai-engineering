// Ambient declarations for Bun's `with { type: "file" }` asset imports (blueprint 07:
// the binary is the payload). Each upstream non-TS extension gets a string default.
declare module "*.md" {
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

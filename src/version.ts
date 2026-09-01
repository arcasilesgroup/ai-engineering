// Single source of the product version: package.json is the only place a
// version number is written; the binary reads it at import. `bun build
// --compile` embeds the JSON, so no filesystem access happens at runtime.
import pkg from "../package.json";

export const VERSION: string = pkg.version;

import Ajv2020, {
  type ErrorObject,
  type ValidateFunction,
} from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

import {
  ValidationError,
  type Result,
  err,
  ok,
} from "../../shared/kernel/index.ts";

import skillSchema from "../../../../../shared/schemas/skill.schema.json" with { type: "json" };
import pluginSchema from "../../../../../shared/schemas/plugin.schema.json" with { type: "json" };

/**
 * ValidateManifest — runs an unknown manifest object through the canonical
 * JSON Schemas at `shared/schemas/{skill,plugin}.schema.json`.
 *
 * Constitution Article V (Single Source of Truth) + Article VI (Supply Chain
 * Integrity): every skill or plugin loaded by the framework MUST validate
 * against its schema. The application layer composes Ajv as a port-less
 * dependency because schemas are static assets — there is no swap need.
 *
 * Returns the validated manifest as a frozen object so downstream callers
 * can keep treating the value as immutable input. Errors collapse to a
 * single `ValidationError` whose message lists every Ajv error path so
 * callers can render a human-readable diagnostic.
 */
export type ManifestKind = "skill" | "plugin";

type ManifestKindMap = {
  readonly skill: SkillManifest;
  readonly plugin: PluginManifest;
};

export interface SkillManifest {
  readonly name: string;
  readonly description: string;
  readonly effort: "max" | "high" | "medium" | "low";
  readonly tier: "core" | "regulated" | "plugin";
  readonly capabilities?: ReadonlyArray<string>;
  readonly modelClass?: string;
  readonly handlers?: ReadonlyArray<string>;
  readonly governance?: { readonly blocking?: boolean };
}

export interface PluginManifest {
  readonly schema_version: "1";
  readonly plugin: Readonly<Record<string, unknown>>;
  readonly compatibility: Readonly<Record<string, unknown>>;
  readonly provides: Readonly<Record<string, unknown>>;
  readonly trust: Readonly<Record<string, unknown>>;
}

// Ajv2020 / addFormats ship CJS default exports; bun + verbatimModuleSyntax
// surface them as namespace records, so we coerce once and cache.
const Ajv =
  (Ajv2020 as unknown as { default: typeof Ajv2020 }).default ?? Ajv2020;
const formats =
  (addFormats as unknown as { default: typeof addFormats }).default ??
  addFormats;

const ajv = new Ajv({ allErrors: true, strict: false });
formats(ajv);

const validators: Readonly<Record<ManifestKind, ValidateFunction>> =
  Object.freeze({
    skill: ajv.compile(skillSchema),
    plugin: ajv.compile(pluginSchema),
  });

const formatErrors = (errors: ReadonlyArray<ErrorObject>): string =>
  errors
    .map((e) => `${e.instancePath || "/"} ${e.message ?? "invalid"}`)
    .join("; ");

export function validateManifest(
  manifest: unknown,
  kind: "skill",
): Result<SkillManifest, ValidationError>;
export function validateManifest(
  manifest: unknown,
  kind: "plugin",
): Result<PluginManifest, ValidationError>;
export function validateManifest<K extends ManifestKind>(
  manifest: unknown,
  kind: K,
): Result<ManifestKindMap[K], ValidationError>;
export function validateManifest(
  manifest: unknown,
  kind: ManifestKind,
): Result<SkillManifest | PluginManifest, ValidationError> {
  if (manifest === null || typeof manifest !== "object") {
    return err(
      new ValidationError(
        `Manifest must be a non-null object (got ${manifest === null ? "null" : typeof manifest})`,
        "manifest",
      ),
    );
  }
  const validate = validators[kind];
  if (!validate) {
    return err(
      new ValidationError(
        `Unknown manifest kind "${String(kind)}" (expected "skill" or "plugin")`,
        "kind",
      ),
    );
  }
  if (!validate(manifest)) {
    const detail = formatErrors(validate.errors ?? []);
    return err(
      new ValidationError(
        `Manifest failed schema validation: ${detail || "unknown reason"}`,
        kind,
      ),
    );
  }
  return ok(
    Object.freeze({ ...(manifest as Record<string, unknown>) }) as
      | SkillManifest
      | PluginManifest,
  );
}

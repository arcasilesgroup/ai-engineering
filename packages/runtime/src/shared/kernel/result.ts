/**
 * Result type — explicit success/failure without exceptions.
 *
 * Inspired by Rust's `Result<T, E>` and the railway-oriented programming
 * pattern. The domain layer never throws; it returns `Result` values that
 * the application layer composes. Exceptions only live at the adapter
 * boundary where we cannot avoid them.
 */
export type Result<T, E = Error> =
  | { readonly ok: true; readonly value: T }
  | { readonly ok: false; readonly error: E };

export const ok = <T>(value: T): Result<T, never> => ({ ok: true, value });

export const err = <E>(error: E): Result<never, E> => ({ ok: false, error });

export const isOk = <T, E>(r: Result<T, E>): r is { ok: true; value: T } =>
  r.ok;

export const isErr = <T, E>(r: Result<T, E>): r is { ok: false; error: E } =>
  !r.ok;

export const map = <T, U, E>(
  r: Result<T, E>,
  fn: (value: T) => U,
): Result<U, E> => (r.ok ? ok(fn(r.value)) : r);

export const mapErr = <T, E, F>(
  r: Result<T, E>,
  fn: (error: E) => F,
): Result<T, F> => (r.ok ? r : err(fn(r.error)));

export const flatMap = <T, U, E>(
  r: Result<T, E>,
  fn: (value: T) => Result<U, E>,
): Result<U, E> => (r.ok ? fn(r.value) : r);

export const unwrapOr = <T, E>(r: Result<T, E>, fallback: T): T =>
  r.ok ? r.value : fallback;

/**
 * Combines an array of Results into a single Result of arrays.
 * Fails fast on the first error encountered.
 */
export const combine = <T, E>(
  results: ReadonlyArray<Result<T, E>>,
): Result<T[], E> => {
  const values: T[] = [];
  for (const r of results) {
    if (!r.ok) return r;
    values.push(r.value);
  }
  return ok(values);
};

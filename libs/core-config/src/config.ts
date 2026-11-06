export class MissingConfigError extends Error {
  constructor(readonly missing: readonly string[]) {
    super(`Missing required configuration: ${missing.join(', ')}`);
    this.name = 'MissingConfigError';
  }
}

type Env = Record<string, string | undefined>;

/**
 * Reads the named environment variables. A variable that is unset or empty is
 * missing. The error names the missing variables and never carries a value.
 */
export function readConfig<K extends string>(
  names: readonly K[],
  env: Env,
): Record<K, string> {
  const missing = names.filter((name) => !env[name]);
  if (missing.length > 0) {
    throw new MissingConfigError(missing);
  }
  return Object.fromEntries(names.map((name) => [name, env[name]])) as Record<
    K,
    string
  >;
}

/** Start-up helper: prints the error to stderr and exits with code 1. */
export function readConfigOrExit<K extends string>(
  names: readonly K[],
  env: Env,
): Record<K, string> {
  try {
    return readConfig(names, env);
  } catch (error) {
    if (error instanceof MissingConfigError) {
      process.stderr.write(`${error.message}\n`);
      process.exit(1);
    }
    throw error;
  }
}

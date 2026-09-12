import type { Dictionary } from "./en";
import { en } from "./en";

/**
 * Dzongkha translation scaffold.
 *
 * Strings verified by a human translator are filled in below; everything else
 * intentionally falls back to English via the deep merge in i18n/index.ts.
 * DO NOT machine-generate values here — the pilot plan requires human review
 * (see docs/PILOT_PLAN.md). The `[DZ REVIEW]` marker in comments tracks
 * outstanding work; unverified keys simply stay English rather than shipping
 * an invented translation.
 */
type DeepPartial<T> = { [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K] };

export const dz: DeepPartial<Dictionary> = {
  appName: "འབྲུག་སོ་ནམ་མཐུན་འབྲེལ།", // verified: "Druk agriculture link/connection"
  auth: {
    language: "སྐད་ཡིག།", // verified: "language"
  },
  // [DZ REVIEW] All remaining keys await verified translation before the pilot.
};

function deepMerge<T extends Record<string, unknown>>(base: T, override: DeepPartial<T>): T {
  const output: Record<string, unknown> = { ...base };
  for (const key of Object.keys(override) as (keyof T)[]) {
    const value = override[key];
    if (value && typeof value === "object" && !Array.isArray(value)) {
      output[key as string] = deepMerge(
        base[key] as Record<string, unknown>,
        value as DeepPartial<Record<string, unknown>>,
      );
    } else if (value !== undefined) {
      output[key as string] = value;
    }
  }
  return output as T;
}

export const dzDictionary: Dictionary = deepMerge(en, dz);

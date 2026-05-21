/**
 * Anthropic Admin API Cost Tracker
 *
 * Queries the Anthropic Usage API to get actual billed costs.
 * Admin key is read from project-level .env file (not global Paperclip config).
 *
 * Security:
 * - Key read from mounted workspace .env only
 * - Key never logged
 * - HTTPS only
 */

import { readFileSync } from "fs";
import { resolve } from "path";

// Cache the admin key after first read
let cachedAdminKey: string | null = null;
let keyLoadAttempted = false;

// Workspace path where SimplifyOps is mounted
const WORKSPACE_ENV_PATH = "/workspace/simplifyops/.env";

// Anthropic Admin API base URL
const ADMIN_API_BASE = "https://api.anthropic.com/v1/organizations";

/**
 * Load admin API key from project .env file
 * Returns null if not found (cost tracking disabled)
 */
function loadAdminKey(): string | null {
  if (keyLoadAttempted) return cachedAdminKey;
  keyLoadAttempted = true;

  try {
    const envContent = readFileSync(WORKSPACE_ENV_PATH, "utf-8");
    const match = envContent.match(/^ANTHROPIC_ADMIN_API_KEY=(.+)$/m);
    if (match && match[1]) {
      cachedAdminKey = match[1].trim();
      console.log("[anthropic-cost] Admin API key loaded from workspace .env");
    } else {
      console.log("[anthropic-cost] No ANTHROPIC_ADMIN_API_KEY in workspace .env - cost tracking disabled");
    }
  } catch (err) {
    console.log("[anthropic-cost] Could not read workspace .env - cost tracking disabled");
  }

  return cachedAdminKey;
}

/**
 * Query Anthropic Usage API for a specific time window
 * Returns usage data including token counts and cost
 */
export async function queryUsage(options: {
  startTime: Date;
  endTime: Date;
  timeBucket?: "1m" | "1h" | "1d";
}): Promise<{
  inputTokens: number;
  outputTokens: number;
  cachedInputTokens: number;
  costUsd: number;
} | null> {
  const adminKey = loadAdminKey();
  if (!adminKey) return null;

  const { startTime, endTime, timeBucket = "1m" } = options;

  const params = new URLSearchParams({
    start_time: startTime.toISOString(),
    end_time: endTime.toISOString(),
    time_bucket: timeBucket,
  });

  try {
    const response = await fetch(
      `${ADMIN_API_BASE}/usage_report/messages?${params}`,
      {
        method: "GET",
        headers: {
          "x-api-key": adminKey,
          "anthropic-version": "2023-06-01",
        },
      }
    );

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[anthropic-cost] API error ${response.status}: ${errorText}`);
      return null;
    }

    const data = await response.json();

    // Aggregate all buckets in the response
    let inputTokens = 0;
    let outputTokens = 0;
    let cachedInputTokens = 0;
    let costUsd = 0;

    if (Array.isArray(data.data)) {
      for (const bucket of data.data) {
        inputTokens += bucket.input_tokens ?? 0;
        outputTokens += bucket.output_tokens ?? 0;
        cachedInputTokens += bucket.cache_read_input_tokens ?? 0;
        // Cost is returned in USD
        costUsd += bucket.cost_usd ?? 0;
      }
    }

    return { inputTokens, outputTokens, cachedInputTokens, costUsd };
  } catch (err) {
    console.error("[anthropic-cost] Failed to query usage API:", err);
    return null;
  }
}

/**
 * Get cost for a specific run by querying usage before and after
 * This is called by the heartbeat service after a run completes
 */
export async function getRunCost(options: {
  runStartTime: Date;
  runEndTime: Date;
  fallbackInputTokens?: number;
  fallbackOutputTokens?: number;
  model?: string;
}): Promise<{
  costCents: number;
  source: "admin_api" | "calculated" | "none";
  inputTokens?: number;
  outputTokens?: number;
}> {
  const { runStartTime, runEndTime, fallbackInputTokens, fallbackOutputTokens, model } = options;

  // Try to get actual cost from Admin API
  const usage = await queryUsage({
    startTime: runStartTime,
    endTime: runEndTime,
    timeBucket: "1m",
  });

  if (usage && usage.costUsd > 0) {
    return {
      costCents: Math.round(usage.costUsd * 100),
      source: "admin_api",
      inputTokens: usage.inputTokens,
      outputTokens: usage.outputTokens,
    };
  }

  // Fallback: calculate from tokens if we have them
  if (fallbackInputTokens || fallbackOutputTokens) {
    const costCents = calculateCostFromTokens({
      inputTokens: fallbackInputTokens ?? 0,
      outputTokens: fallbackOutputTokens ?? 0,
      model: model ?? "claude-sonnet-4-20250514",
    });
    return {
      costCents,
      source: "calculated",
      inputTokens: fallbackInputTokens,
      outputTokens: fallbackOutputTokens,
    };
  }

  return { costCents: 0, source: "none" };
}

/**
 * Fallback: Calculate cost from tokens using known pricing
 * Only used when Admin API is unavailable
 */
function calculateCostFromTokens(options: {
  inputTokens: number;
  outputTokens: number;
  model: string;
}): number {
  const { inputTokens, outputTokens, model } = options;

  // Pricing per million tokens (as of 2026)
  const pricing: Record<string, { input: number; output: number }> = {
    // Claude 4.x models
    "claude-opus-4": { input: 15.0, output: 75.0 },
    "claude-sonnet-4": { input: 3.0, output: 15.0 },
    "claude-haiku-4": { input: 0.25, output: 1.25 },
    // Fallback for unknown models
    "default": { input: 3.0, output: 15.0 },
  };

  // Find matching pricing (partial match on model name)
  let rates = pricing["default"];
  for (const [key, value] of Object.entries(pricing)) {
    if (model.toLowerCase().includes(key)) {
      rates = value;
      break;
    }
  }

  const inputCost = (inputTokens / 1_000_000) * rates.input;
  const outputCost = (outputTokens / 1_000_000) * rates.output;
  const totalUsd = inputCost + outputCost;

  return Math.round(totalUsd * 100); // Convert to cents
}

/**
 * Check if cost tracking is available (admin key configured)
 */
export function isCostTrackingEnabled(): boolean {
  return loadAdminKey() !== null;
}

/**
 * Heartbeat Cost Tracking Patch
 *
 * This file shows the modifications needed to server/src/services/heartbeat.ts
 * to integrate Anthropic Admin API cost tracking.
 *
 * Apply these changes manually or use the apply script below.
 */

// =============================================================================
// CHANGE 1: Add import at top of file (after other imports)
// =============================================================================
// Add this line:
import { getRunCost } from "./anthropic-cost-tracker.js";

// =============================================================================
// CHANGE 2: Modify updateRuntimeState function
// =============================================================================
// Find this section (around line 1855-1858):
//
//   const billingType = normalizeLedgerBillingType(result.billingType);
//   const additionalCostCents = normalizeBilledCostCents(result.costUsd, billingType);
//   const hasTokenUsage = inputTokens > 0 || outputTokens > 0 || cachedInputTokens > 0;
//
// Replace with:
//
//   const billingType = normalizeLedgerBillingType(result.billingType);
//   let additionalCostCents = normalizeBilledCostCents(result.costUsd, billingType);
//   const hasTokenUsage = inputTokens > 0 || outputTokens > 0 || cachedInputTokens > 0;
//
//   // If no cost from adapter but we have token usage, query Anthropic Admin API
//   if (additionalCostCents === 0 && hasTokenUsage) {
//     const runCost = await getRunCost({
//       runStartTime: run.createdAt,
//       runEndTime: new Date(),
//       fallbackInputTokens: inputTokens,
//       fallbackOutputTokens: outputTokens,
//       model: result.model,
//     });
//     if (runCost.costCents > 0) {
//       additionalCostCents = runCost.costCents;
//       console.log(`[heartbeat] Cost from ${runCost.source}: ${additionalCostCents} cents`);
//     }
//   }

// =============================================================================
// APPLY SCRIPT (run from ~/paperclip-wsl/paperclip-source)
// =============================================================================
/*
#!/bin/bash
# apply-cost-patch.sh

HEARTBEAT_FILE="server/src/services/heartbeat.ts"
COST_TRACKER="server/src/services/anthropic-cost-tracker.ts"

# Copy cost tracker module
cp /workspace/simplifyops/plan-architecture/paperclip-patches/anthropic-cost-tracker.ts "$COST_TRACKER"

# Add import (if not already present)
if ! grep -q 'anthropic-cost-tracker' "$HEARTBEAT_FILE"; then
  sed -i '1a import { getRunCost } from "./anthropic-cost-tracker.js";' "$HEARTBEAT_FILE"
fi

# Replace the cost calculation section
sed -i 's/const additionalCostCents = normalizeBilledCostCents/let additionalCostCents = normalizeBilledCostCents/' "$HEARTBEAT_FILE"

echo "Patch applied. Now rebuild: docker compose up -d server --build"
*/

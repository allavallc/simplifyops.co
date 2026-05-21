// Copyright (c) 2026 The Hana Sachiko Company, Inc. All rights reserved.
// Proprietary and confidential.

import path from "node:path";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import type { AdapterExecutionContext, AdapterExecutionResult } from "@hana-core/adapter-utils";
import {
  asString,
  asNumber,
  asStringArray,
  parseObject,
  buildHanaCoreEnv,
  redactEnvForLogs,
  renderTemplate,
  joinPromptSections,
  runChildProcess,
} from "@hana-core/adapter-utils/server-utils";
import { parseHermesOutput } from "./parse.js";

const __moduleDir = path.dirname(fileURLToPath(import.meta.url));

/**
 * Resolve the hermes/ directory.
 */
function resolveHermesDir(): string {
  const candidates = [
    path.resolve(__moduleDir, "../../../../../hermes"),
    path.resolve(process.cwd(), "hermes"),
  ];
  for (const candidate of candidates) {
    if (existsSync(path.join(candidate, "run_agent.py"))) {
      return candidate;
    }
  }
  return path.resolve(process.cwd(), "hermes");
}

export async function execute(ctx: AdapterExecutionContext): Promise<AdapterExecutionResult> {
  const { runId, agent, runtime, config, context, onLog, onMeta, onSpawn } = ctx;

  const hermesDir = resolveHermesDir();
  const model = asString(config.model, "anthropic/claude-opus-4.6");
  const baseUrl = asString(config.baseUrl, "https://openrouter.ai/api/v1");
  const soulFile = asString(config.soulFile, path.join(hermesDir, "souls", "hana-sachiko.md"));
  const maxTurns = asNumber(config.maxTurns, 10);
  const enabledToolsets = asString(config.enabledToolsets, "");
  const disabledToolsets = asString(config.disabledToolsets, "");
  const cwd = asString(config.cwd, hermesDir);
  const timeoutSec = asNumber(config.timeoutSec, 0);
  const graceSec = asNumber(config.graceSec, 30);
  const extraArgs = asStringArray(config.extraArgs);

  // Build prompt from template
  const promptTemplate = asString(
    config.promptTemplate,
    "You are agent {{agent.id}} ({{agent.name}}). Continue your Hana Core work.",
  );
  const templateData = {
    agentId: agent.id,
    companyId: agent.companyId,
    runId,
    company: { id: agent.companyId },
    agent,
    run: { id: runId, source: "on_demand" },
    context,
  };
  const renderedPrompt = renderTemplate(promptTemplate, templateData);
  const sessionHandoffNote = asString(context.hanaCoreSessionHandoffMarkdown, "").trim();
  const prompt = joinPromptSections([sessionHandoffNote, renderedPrompt]);

  // Build environment
  const envConfig = parseObject(config.env);
  const env: Record<string, string> = { ...buildHanaCoreEnv(agent) };
  env.HANA_RUN_ID = runId;
  if (soulFile) env.HERMES_SOUL_FILE = soulFile;

  for (const [key, value] of Object.entries(envConfig)) {
    if (typeof value === "string") env[key] = value;
  }

  // Build command args
  const args = [
    "run_agent.py",
    "--model", model,
    "--base_url", baseUrl,
    "--max_turns", String(maxTurns),
    "--json_output",
  ];
  if (enabledToolsets) args.push("--enabled_toolsets", enabledToolsets);
  if (disabledToolsets) args.push("--disabled_toolsets", disabledToolsets);
  if (extraArgs.length > 0) args.push(...extraArgs);
  args.push("--query", prompt);

  if (onMeta) {
    await onMeta({
      adapterType: "hermes_local",
      command: "python3",
      cwd,
      commandArgs: args,
      env: redactEnvForLogs(env),
      prompt,
      promptMetrics: { promptChars: prompt.length },
      context,
    });
  }

  const proc = await runChildProcess(runId, "python3", args, {
    cwd,
    env,
    timeoutSec,
    graceSec,
    onSpawn,
    onLog,
  });

  if (proc.timedOut) {
    return {
      exitCode: proc.exitCode,
      signal: proc.signal,
      timedOut: true,
      errorMessage: `Hermes timed out after ${timeoutSec}s`,
      errorCode: "timeout",
    };
  }

  const parsed = parseHermesOutput(proc.stdout);

  if (parsed.errorMessage) {
    return {
      exitCode: proc.exitCode,
      signal: proc.signal,
      timedOut: false,
      errorMessage: parsed.errorMessage,
      errorCode: "hermes_error",
      usage: parsed.usage ?? undefined,
      costUsd: parsed.costUsd,
      provider: "openrouter",
      biller: "openrouter",
      model,
      billingType: "api",
      summary: parsed.summary || null,
      resultJson: { stdout: proc.stdout, stderr: proc.stderr },
    };
  }

  if ((proc.exitCode ?? 0) !== 0 && !parsed.summary) {
    const stderrLine = proc.stderr
      .split(/\r?\n/)
      .map((l) => l.trim())
      .find(Boolean) ?? "";
    return {
      exitCode: proc.exitCode,
      signal: proc.signal,
      timedOut: false,
      errorMessage: stderrLine
        ? `Hermes exited with code ${proc.exitCode ?? -1}: ${stderrLine}`
        : `Hermes exited with code ${proc.exitCode ?? -1}`,
      resultJson: { stdout: proc.stdout, stderr: proc.stderr },
    };
  }

  return {
    exitCode: proc.exitCode,
    signal: proc.signal,
    timedOut: false,
    errorMessage: (proc.exitCode ?? 0) !== 0
      ? `Hermes exited with code ${proc.exitCode ?? -1}`
      : null,
    usage: parsed.usage ?? undefined,
    costUsd: parsed.costUsd,
    provider: "openrouter",
    biller: "openrouter",
    model,
    billingType: "api",
    summary: parsed.summary || null,
    resultJson: parsed.jsonMode ? { lines: parsed.lines } : { stdout: proc.stdout },
  };
}
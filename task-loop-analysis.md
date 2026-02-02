# Task and Loop Processing Architecture

This document provides a detailed analysis of how tasks are defined, scheduled, and processed in the OpenClaw codebase.

## Table of Contents

1. [Overview](#overview)
2. [Core Task Systems](#core-task-systems)
   - [Command Queue](#1-command-queue)
   - [Cron Job System](#2-cron-job-system)
   - [Followup Queue](#3-followup-queue)
   - [Gateway Run Loop](#4-gateway-run-loop)
3. [Task Type Definitions](#task-type-definitions)
   - [CronJob Structure](#cronjob-structure)
   - [FollowupRun Structure](#followuprun-structure)
4. [User-Defined Task Payloads](#user-defined-task-payloads)
   - [CLI Interface](#cli-interface)
   - [Agent Tool Interface](#agent-tool-interface)
5. [Execution Flow](#execution-flow)
6. [File Reference](#file-reference)

---

## Overview

OpenClaw uses a multi-layered task processing architecture consisting of:

| Layer | Purpose | Persistence |
|-------|---------|-------------|
| **Command Queue** | Serializes execution across lanes | In-memory |
| **Cron Service** | Timer-driven scheduled tasks | Disk (`cron.json`) |
| **Followup Queue** | Queues messages while agent busy | In-memory |
| **Gateway Loop** | Keeps process alive with restart capability | N/A |

These systems work together to provide ordered execution, scheduled tasks, and graceful handling of concurrent message arrival.

---

## Core Task Systems

### 1. Command Queue

**Location:** `src/process/command-queue.ts`

The command queue is the foundational serialization layer. It ensures tasks within the same "lane" execute sequentially while allowing parallelism across different lanes.

#### Queue Entry Structure

```typescript
type QueueEntry = {
  task: () => Promise<unknown>;
  resolve: (value: unknown) => void;
  reject: (reason?: unknown) => void;
  enqueuedAt: number;
  warnAfterMs: number;
  onWait?: (waitMs: number, queuedAhead: number) => void;
};
```

#### Lane State

```typescript
type LaneState = {
  lane: string;
  queue: QueueEntry[];
  active: number;
  maxConcurrent: number;
  draining: boolean;
};
```

#### API

```typescript
// Enqueue to default "main" lane
export function enqueueCommand<T>(task: () => Promise<T>): Promise<T>

// Enqueue to a specific lane
export function enqueueCommandInLane<T>(lane: string, task: () => Promise<T>): Promise<T>

// Configure per-lane concurrency
export function setCommandLaneConcurrency(lane: string, max: number): void
```

#### Defined Lanes

**Location:** `src/process/lanes.ts`

```typescript
export const enum CommandLane {
  Main = "main",        // Default auto-reply workflow
  Cron = "cron",        // Scheduled job processing
  Subagent = "subagent", // Sub-agent execution
  Nested = "nested",    // Nested agent calls
}
```

#### Lane Concurrency Configuration

**Location:** `src/gateway/server-lanes.ts`

```typescript
export function applyGatewayLaneConcurrency(cfg: ReturnType<typeof loadConfig>) {
  setCommandLaneConcurrency(CommandLane.Cron, cfg.cron?.maxConcurrentRuns ?? 1);
  setCommandLaneConcurrency(CommandLane.Main, resolveAgentMaxConcurrent(cfg));
  setCommandLaneConcurrency(CommandLane.Subagent, resolveSubagentMaxConcurrent(cfg));
}
```

---

### 2. Cron Job System

**Location:** `src/cron/`

The cron system provides timer-driven task scheduling with support for one-shot, interval, and cron-expression schedules.

#### Architecture

```
src/cron/
├── service.ts              # CronService class (main entry)
├── types.ts                # Type definitions
├── normalize.ts            # Input normalization
├── schedule.ts             # Schedule computation
├── isolated-agent.ts       # Isolated job execution
└── service/
    ├── jobs.ts             # Job creation/patching
    ├── timer.ts            # Timer loop logic
    ├── ops.ts              # RPC operations
    └── store.ts            # Persistence
```

#### Timer Loop

**Location:** `src/cron/service/timer.ts`

```typescript
// Arm the timer for the next due job
export function armTimer(state: CronServiceState) {
  const nextAt = nextWakeAtMs(state);
  if (!nextAt) return;
  const delay = Math.max(nextAt - state.deps.nowMs(), 0);
  state.timer = setTimeout(() => {
    void onTimer(state).catch(...);
  }, delay);
}

// Timer expiry handler
export async function onTimer(state: CronServiceState) {
  if (state.running) return; // Prevent concurrent execution
  state.running = true;
  try {
    await locked(state, async () => {
      await ensureLoaded(state);
      await runDueJobs(state);
      await persist(state);
      armTimer(state);
    });
  } finally {
    state.running = false;
  }
}

// Execute all jobs that are due
export async function runDueJobs(state: CronServiceState) {
  const now = state.deps.nowMs();
  const due = state.store.jobs.filter((j) =>
    j.enabled &&
    !j.state.runningAtMs &&
    typeof j.state.nextRunAtMs === "number" &&
    now >= j.state.nextRunAtMs
  );
  for (const job of due) {
    await executeJob(state, job, now, { forced: false });
  }
}
```

#### Schedule Types

```typescript
export type CronSchedule =
  | { kind: "at"; atMs: number }                      // One-shot at timestamp
  | { kind: "every"; everyMs: number; anchorMs?: number }  // Recurring interval
  | { kind: "cron"; expr: string; tz?: string };      // Cron expression
```

| Kind | Description | Example |
|------|-------------|---------|
| `at` | One-shot execution at absolute timestamp | `{ kind: "at", atMs: 1706810400000 }` |
| `every` | Recurring interval with optional anchor | `{ kind: "every", everyMs: 3600000 }` |
| `cron` | Standard 5-field cron expression | `{ kind: "cron", expr: "0 9 * * 1-5", tz: "America/New_York" }` |

#### Payload Types

```typescript
export type CronPayload =
  | { kind: "systemEvent"; text: string }
  | {
      kind: "agentTurn";
      message: string;
      model?: string;
      thinking?: string;
      timeoutSeconds?: number;
      allowUnsafeExternalContent?: boolean;
      deliver?: boolean;
      channel?: CronMessageChannel;
      to?: string;
      bestEffortDeliver?: boolean;
    };
```

| Kind | Session Target | Description |
|------|----------------|-------------|
| `systemEvent` | `main` | Injects text as system event into main session |
| `agentTurn` | `isolated` | Runs full agent turn with optional delivery |

#### Wake Modes

```typescript
export type CronWakeMode = "next-heartbeat" | "now";
```

| Mode | Behavior |
|------|----------|
| `next-heartbeat` | Job waits for next scheduled heartbeat |
| `now` | Job triggers immediate agent wake |

---

### 3. Followup Queue

**Location:** `src/auto-reply/reply/queue/`

The followup queue handles messages that arrive while the agent is busy processing another request.

#### Architecture

```
src/auto-reply/reply/queue/
├── queue.ts      # Exports
├── state.ts      # Queue state management
├── types.ts      # Type definitions
├── enqueue.ts    # Enqueue logic
└── drain.ts      # Drain loop
```

#### Queue State

**Location:** `src/auto-reply/reply/queue/state.ts`

```typescript
export type FollowupQueueState = {
  items: FollowupRun[];
  draining: boolean;
  lastEnqueuedAt: number;
  mode: QueueMode;
  debounceMs: number;
  cap: number;
  dropPolicy: QueueDropPolicy;
  droppedCount: number;
  summaryLines: string[];
  lastRun?: FollowupRun["run"];
};

export const FOLLOWUP_QUEUES = new Map<string, FollowupQueueState>();
```

#### Queue Modes

```typescript
export type QueueMode = "steer" | "followup" | "collect" | "steer-backlog" | "interrupt" | "queue";
```

| Mode | Behavior |
|------|----------|
| `collect` | Batches same-channel messages into single prompt |
| `followup` | Processes messages one at a time |
| `steer` | Steering mode for conversation control |
| `interrupt` | Allows interruption of current processing |

#### Drop Policies

```typescript
export type QueueDropPolicy = "old" | "new" | "summarize";
```

| Policy | Behavior when queue full |
|--------|--------------------------|
| `old` | Drop oldest messages |
| `new` | Reject new messages |
| `summarize` | Summarize dropped messages |

#### Drain Loop

**Location:** `src/auto-reply/reply/queue/drain.ts`

```typescript
export function scheduleFollowupDrain(
  key: string,
  runFollowup: (run: FollowupRun) => Promise<void>,
): void {
  const queue = FOLLOWUP_QUEUES.get(key);
  if (!queue || queue.draining) return;
  queue.draining = true;

  void (async () => {
    try {
      while (queue.items.length > 0 || queue.droppedCount > 0) {
        await waitForQueueDebounce(queue);

        if (queue.mode === "collect") {
          const isCrossChannel = hasCrossChannelItems(queue.items, ...);
          if (isCrossChannel) {
            // Process individually for cross-channel routing
            const next = queue.items.shift();
            await runFollowup(next);
          } else {
            // Batch all into one prompt
            const items = queue.items.splice(0, queue.items.length);
            const prompt = buildCollectPrompt({
              title: "[Queued messages while agent was busy]",
              items,
              renderItem: (item, idx) => `---\nQueued #${idx + 1}\n${item.prompt}`,
            });
            await runFollowup({ prompt, run, ... });
          }
        } else {
          // Process one at a time
          const next = queue.items.shift();
          await runFollowup(next);
        }
      }
    } finally {
      queue.draining = false;
      if (queue.items.length > 0 || queue.droppedCount > 0) {
        scheduleFollowupDrain(key, runFollowup);
      } else {
        FOLLOWUP_QUEUES.delete(key);
      }
    }
  })();
}
```

---

### 4. Gateway Run Loop

**Location:** `src/cli/gateway-cli/run-loop.ts`

The gateway run loop is the top-level process loop that keeps the gateway alive and handles signals.

```typescript
export async function runGatewayLoop(params: {
  start: () => Promise<Awaited<ReturnType<typeof startGatewayServer>>>;
  runtime: typeof defaultRuntime;
}) {
  const lock = await acquireGatewayLock();
  let server: GatewayServer | null = null;
  let shuttingDown = false;
  let restartResolver: (() => void) | null = null;

  // Signal handlers
  // SIGUSR1 -> restart
  // SIGTERM/SIGINT -> graceful shutdown (5s timeout)

  // Keep process alive
  while (true) {
    server = await params.start();
    await new Promise<void>((resolve) => {
      restartResolver = resolve;
    });
  }
}
```

#### Signal Handling

| Signal | Action |
|--------|--------|
| `SIGUSR1` | In-process restart (no supervisor needed) |
| `SIGTERM` | Graceful shutdown with 5s timeout |
| `SIGINT` | Graceful shutdown with 5s timeout |

---

## Task Type Definitions

### CronJob Structure

**Location:** `src/cron/types.ts`

```typescript
export type CronJob = {
  // Identity
  id: string;
  agentId?: string;
  name: string;
  description?: string;

  // Lifecycle
  enabled: boolean;
  deleteAfterRun?: boolean;
  createdAtMs: number;
  updatedAtMs: number;

  // Scheduling
  schedule: CronSchedule;
  sessionTarget: CronSessionTarget;  // "main" | "isolated"
  wakeMode: CronWakeMode;            // "now" | "next-heartbeat"

  // Execution
  payload: CronPayload;
  isolation?: CronIsolation;

  // Runtime state
  state: CronJobState;
};

export type CronJobState = {
  nextRunAtMs?: number;
  runningAtMs?: number;
  lastRunAtMs?: number;
  lastStatus?: "ok" | "error" | "skipped";
  lastError?: string;
  lastDurationMs?: number;
};

export type CronIsolation = {
  postToMainPrefix?: string;
  postToMainMode?: "summary" | "full";
  postToMainMaxChars?: number;
};
```

#### Complete CronJob Example

```typescript
const exampleCronJob: CronJob = {
  // Identity
  id: "job_abc123",
  agentId: "ops",
  name: "Daily backup reminder",
  description: "Sends a reminder to check backups",

  // Lifecycle
  enabled: true,
  deleteAfterRun: false,
  createdAtMs: 1706637600000,
  updatedAtMs: 1706637600000,

  // Scheduling
  schedule: { kind: "cron", expr: "0 9 * * *", tz: "America/New_York" },
  sessionTarget: "isolated",
  wakeMode: "now",

  // Execution
  payload: {
    kind: "agentTurn",
    message: "Check backup status and report any issues",
    model: "claude-sonnet",
    thinking: "low",
    timeoutSeconds: 120,
    deliver: true,
    channel: "telegram",
    to: "7200373102",
  },

  // Isolation config
  isolation: {
    postToMainPrefix: "Backup Check",
    postToMainMode: "summary",
  },

  // Runtime state (managed by system)
  state: {
    nextRunAtMs: 1706875200000,
    lastRunAtMs: 1706788800000,
    lastStatus: "ok",
    lastDurationMs: 4532,
  },
};
```

---

### FollowupRun Structure

**Location:** `src/auto-reply/reply/queue/types.ts`

```typescript
export type FollowupRun = {
  // Message content
  prompt: string;
  messageId?: string;
  summaryLine?: string;
  enqueuedAt: number;

  // Reply routing
  originatingChannel?: OriginatingChannelType;
  originatingTo?: string;
  originatingAccountId?: string;
  originatingThreadId?: string | number;
  originatingChatType?: string;

  // Execution context
  run: {
    agentId: string;
    agentDir: string;
    sessionId: string;
    sessionKey?: string;
    sessionFile: string;
    workspaceDir: string;

    // Provider context
    messageProvider?: string;
    agentAccountId?: string;
    groupId?: string;
    groupChannel?: string;
    groupSpace?: string;

    // Sender context
    senderId?: string;
    senderName?: string;
    senderUsername?: string;
    senderE164?: string;

    // Model configuration
    provider: string;
    model: string;
    authProfileId?: string;
    thinkLevel?: ThinkLevel;
    verboseLevel?: VerboseLevel;
    reasoningLevel?: ReasoningLevel;
    elevatedLevel?: ElevatedLevel;

    // Execution settings
    timeoutMs: number;
    blockReplyBreak: "text_end" | "message_end";
    ownerNumbers?: string[];
    extraSystemPrompt?: string;
    enforceFinalTag?: boolean;

    // Config snapshot
    config: OpenClawConfig;
    skillsSnapshot?: SkillSnapshot;
    execOverrides?: ExecToolDefaults;
    bashElevated?: {
      enabled: boolean;
      allowed: boolean;
      defaultLevel: ElevatedLevel;
    };
  };
};
```

#### Complete FollowupRun Example

```typescript
const exampleFollowupRun: FollowupRun = {
  // Message
  prompt: "What's the weather like today?",
  messageId: "msg_xyz789",
  summaryLine: "Weather query",
  enqueuedAt: 1706637600000,

  // Reply routing
  originatingChannel: "telegram",
  originatingTo: "7200373102",
  originatingAccountId: "bot_main",
  originatingThreadId: 42,
  originatingChatType: "private",

  // Execution context
  run: {
    agentId: "default",
    agentDir: "/Users/user/.clawdbot/agents/default",
    sessionId: "main",
    sessionFile: "/Users/user/.clawdbot/agents/default/sessions/main.jsonl",
    workspaceDir: "/Users/user/projects",

    senderId: "12345",
    senderName: "Alice",
    senderUsername: "alice_dev",

    provider: "anthropic",
    model: "claude-sonnet-4-20250514",
    thinkLevel: "low",
    timeoutMs: 120000,
    blockReplyBreak: "message_end",

    config: { /* OpenClawConfig snapshot */ },
  },
};
```

---

## User-Defined Task Payloads

Users can create cron jobs with custom payloads through two interfaces.

### CLI Interface

**Location:** `src/cli/cron-cli/register.cron-add.ts`

#### Command Syntax

```bash
openclaw cron add [options]
```

#### Required Options

| Option | Description |
|--------|-------------|
| `--name <name>` | Job name |
| Schedule (pick one): | |
| `--at <when>` | One-shot at ISO time or `+duration` |
| `--every <duration>` | Recurring interval (e.g., `10m`, `1h`) |
| `--cron <expr>` | 5-field cron expression |
| Payload (pick one): | |
| `--system-event <text>` | System event (requires `--session main`) |
| `--message <text>` | Agent message (requires `--session isolated`) |

#### Optional Options

| Option | Default | Description |
|--------|---------|-------------|
| `--description <text>` | - | Job description |
| `--disabled` | `false` | Create job disabled |
| `--delete-after-run` | `false` | Delete one-shot after success |
| `--agent <id>` | - | Agent ID for this job |
| `--session <target>` | `main` | Session target: `main` or `isolated` |
| `--wake <mode>` | `next-heartbeat` | Wake mode: `now` or `next-heartbeat` |
| `--tz <iana>` | - | Timezone for cron expressions |
| `--model <model>` | - | Model override |
| `--thinking <level>` | - | Thinking level: `off`/`minimal`/`low`/`medium`/`high` |
| `--timeout-seconds <n>` | - | Execution timeout |
| `--deliver` | `false` | Deliver agent output |
| `--channel <channel>` | `last` | Delivery channel |
| `--to <dest>` | - | Delivery destination |
| `--best-effort-deliver` | `false` | Don't fail job if delivery fails |
| `--post-prefix <prefix>` | `Cron` | Prefix for main-session post |
| `--post-mode <mode>` | `summary` | Post mode: `summary` or `full` |
| `--post-max-chars <n>` | `8000` | Max chars for full post mode |
| `--json` | `false` | Output JSON |

#### CLI Examples

**One-shot reminder (main session):**
```bash
openclaw cron add \
  --name "Meeting reminder" \
  --at "+30m" \
  --session main \
  --system-event "Your meeting starts in 5 minutes!"
```

**Daily recurring task (isolated session with delivery):**
```bash
openclaw cron add \
  --name "Daily weather report" \
  --cron "0 8 * * *" \
  --tz "America/New_York" \
  --session isolated \
  --message "Check the weather forecast and send a summary" \
  --model "claude-sonnet" \
  --thinking "low" \
  --deliver \
  --channel telegram \
  --to "7200373102"
```

**Hourly interval task:**
```bash
openclaw cron add \
  --name "System health check" \
  --every "1h" \
  --session isolated \
  --message "Run system diagnostics and report any issues" \
  --timeout-seconds 300
```

**One-shot with auto-delete:**
```bash
openclaw cron add \
  --name "Deploy reminder" \
  --at "2024-02-01T14:00:00" \
  --delete-after-run \
  --session main \
  --system-event "Time to deploy the new release!"
```

---

### Agent Tool Interface

**Location:** `src/agents/tools/cron-tool.ts`

The agent can self-serve cron job management through the built-in `cron` tool.

#### Tool Actions

| Action | Required Params | Description |
|--------|-----------------|-------------|
| `status` | - | Check scheduler status |
| `list` | - | List jobs (`includeDisabled: true` for all) |
| `add` | `job` | Create new job |
| `update` | `jobId`, `patch` | Modify existing job |
| `remove` | `jobId` | Delete job |
| `run` | `jobId` | Trigger job immediately |
| `runs` | `jobId` | Get job run history |
| `wake` | `text` | Send wake event |

#### Tool Schema

```typescript
const CronToolSchema = Type.Object({
  action: stringEnum(["status", "list", "add", "update", "remove", "run", "runs", "wake"]),
  gatewayUrl: Type.Optional(Type.String()),
  gatewayToken: Type.Optional(Type.String()),
  timeoutMs: Type.Optional(Type.Number()),
  includeDisabled: Type.Optional(Type.Boolean()),
  job: Type.Optional(Type.Object({}, { additionalProperties: true })),
  jobId: Type.Optional(Type.String()),
  id: Type.Optional(Type.String()),
  patch: Type.Optional(Type.Object({}, { additionalProperties: true })),
  text: Type.Optional(Type.String()),
  mode: optionalStringEnum(["now", "next-heartbeat"]),
  contextMessages: Type.Optional(Type.Number({ minimum: 0, maximum: 10 })),
});
```

#### Agent Tool Examples

**Create a one-shot reminder:**
```json
{
  "action": "add",
  "job": {
    "name": "Grocery reminder",
    "schedule": { "kind": "at", "atMs": 1706810400000 },
    "sessionTarget": "main",
    "payload": {
      "kind": "systemEvent",
      "text": "Don't forget to buy groceries!"
    }
  }
}
```

**Create a recurring report with context:**
```json
{
  "action": "add",
  "job": {
    "name": "Weekly status report",
    "schedule": { "kind": "cron", "expr": "0 9 * * 1", "tz": "UTC" },
    "sessionTarget": "isolated",
    "payload": {
      "kind": "agentTurn",
      "message": "Generate the weekly status report based on recent activity",
      "model": "claude-sonnet",
      "deliver": true,
      "channel": "telegram",
      "to": "7200373102"
    }
  },
  "contextMessages": 5
}
```

**Update a job:**
```json
{
  "action": "update",
  "jobId": "job_abc123",
  "patch": {
    "enabled": false,
    "schedule": { "kind": "cron", "expr": "0 10 * * *" }
  }
}
```

**Trigger immediate execution:**
```json
{
  "action": "run",
  "jobId": "job_abc123"
}
```

---

## Execution Flow

### Cron Job Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     Gateway Startup                              │
├─────────────────────────────────────────────────────────────────┤
│  1. applyGatewayLaneConcurrency()                               │
│     └── Set per-lane concurrency limits                         │
│  2. buildGatewayCronService()                                   │
│     └── Initialize CronService with deps                        │
│  3. armTimer()                                                  │
│     └── Schedule first timer wake                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Timer Loop                                   │
├─────────────────────────────────────────────────────────────────┤
│  1. setTimeout() expires                                        │
│  2. onTimer() called                                            │
│     ├── Check if already running (prevent concurrent)           │
│     └── Acquire lock                                            │
│  3. ensureLoaded() - load jobs from disk                        │
│  4. runDueJobs()                                                │
│     ├── Filter: enabled && !running && now >= nextRunAtMs       │
│     └── For each due job: executeJob()                          │
│  5. persist() - save state to disk                              │
│  6. armTimer() - schedule next wake                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Job Execution                                │
├─────────────────────────────────────────────────────────────────┤
│  payload.kind = "systemEvent"                                   │
│  └── enqueueSystemEvent(text)                                   │
│      └── Inject into main session                               │
│                                                                 │
│  payload.kind = "agentTurn"                                     │
│  └── runIsolatedAgentJob(job)                                   │
│      ├── Create isolated session                                │
│      ├── Run agent turn with message                            │
│      ├── Optionally deliver output                              │
│      └── Post summary/result to main session                    │
└─────────────────────────────────────────────────────────────────┘
```

### Followup Queue Processing Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                   Message Arrival                                │
├─────────────────────────────────────────────────────────────────┤
│  1. Message arrives while agent busy                            │
│  2. enqueueFollowupRun()                                        │
│     ├── Check deduplication (messageId or prompt)               │
│     ├── Check queue cap                                         │
│     ├── Apply drop policy if full                               │
│     └── Add to queue.items[]                                    │
│  3. scheduleFollowupDrain() triggered                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Drain Loop                                   │
├─────────────────────────────────────────────────────────────────┤
│  while (items.length > 0 || droppedCount > 0):                  │
│                                                                 │
│  1. waitForQueueDebounce()                                      │
│     └── Wait debounceMs before processing                       │
│                                                                 │
│  2. Process based on mode:                                      │
│     ├── mode = "collect" && same-channel:                       │
│     │   └── Batch all items into single prompt                  │
│     ├── mode = "collect" && cross-channel:                      │
│     │   └── Process individually (preserve routing)             │
│     └── other modes:                                            │
│         └── Process one item at a time                          │
│                                                                 │
│  3. runFollowup(item)                                           │
│     └── Execute agent turn with queued prompt                   │
│                                                                 │
│  4. If more items arrived during processing:                    │
│     └── Re-schedule drain                                       │
│                                                                 │
│  5. Cleanup: FOLLOWUP_QUEUES.delete(key)                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## File Reference

### Core Task Infrastructure

| File | Purpose |
|------|---------|
| `src/process/command-queue.ts` | Lane-based task queue implementation |
| `src/process/lanes.ts` | Lane name constants |
| `src/gateway/server-lanes.ts` | Lane concurrency configuration |

### Cron System

| File | Purpose |
|------|---------|
| `src/cron/service.ts` | CronService class (main entry) |
| `src/cron/types.ts` | Type definitions |
| `src/cron/normalize.ts` | Input normalization |
| `src/cron/schedule.ts` | Schedule computation (nextRunAtMs) |
| `src/cron/isolated-agent.ts` | Isolated job execution |
| `src/cron/service/jobs.ts` | Job creation and patching |
| `src/cron/service/timer.ts` | Timer loop logic |
| `src/cron/service/ops.ts` | RPC operations |
| `src/cron/service/store.ts` | Job persistence |

### Followup Queue

| File | Purpose |
|------|---------|
| `src/auto-reply/reply/queue/queue.ts` | Queue exports |
| `src/auto-reply/reply/queue/state.ts` | Queue state management |
| `src/auto-reply/reply/queue/types.ts` | FollowupRun type definition |
| `src/auto-reply/reply/queue/enqueue.ts` | Enqueue logic |
| `src/auto-reply/reply/queue/drain.ts` | Drain loop implementation |

### User Interfaces

| File | Purpose |
|------|---------|
| `src/cli/cron-cli/register.cron-add.ts` | CLI `cron add` command |
| `src/agents/tools/cron-tool.ts` | Agent `cron` tool |

### Gateway

| File | Purpose |
|------|---------|
| `src/cli/gateway-cli/run-loop.ts` | Main gateway process loop |
| `src/gateway/server.impl.ts` | Gateway initialization |
| `src/gateway/server-cron.ts` | Cron service setup |
| `src/gateway/server-methods/cron.ts` | Cron RPC methods |

---

## Summary

The OpenClaw task architecture provides:

1. **Ordered execution** via lane-based command queue with configurable concurrency
2. **Scheduled tasks** via timer-driven cron system with three schedule types
3. **Queue management** via followup queue with debouncing and batching
4. **Process resilience** via gateway run loop with signal handling

Users can define custom task payloads through:
- **CLI**: `openclaw cron add` with comprehensive options
- **Agent tool**: Self-service `cron` tool for programmatic job management

The system enforces constraints:
- `sessionTarget="main"` requires `payload.kind="systemEvent"`
- `sessionTarget="isolated"` requires `payload.kind="agentTurn"`

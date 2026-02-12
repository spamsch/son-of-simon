<script lang="ts">
  import { onMount } from "svelte";
  import { Button } from "$lib/components/ui";
  import { Command } from "@tauri-apps/plugin-shell";
  import { open } from "@tauri-apps/plugin-shell";
  import {
    Wrench,
    Check,
    ExternalLink,
    ArrowRight,
    ArrowLeft,
    Info,
    RefreshCw,
  } from "lucide-svelte";
  import { onboardingStore, type DevToolsData } from "$lib/stores/onboarding.svelte";

  interface Props {
    onNext: () => void;
    onBack: () => void;
  }

  let { onNext, onBack }: Props = $props();

  // PATH prefix for Homebrew on Apple Silicon + Intel
  const PATH_PREFIX = "/opt/homebrew/bin:/usr/local/bin";

  let checking = $state(true);
  let homebrew = $state({ installed: false, version: "" });
  let python = $state({ installed: false, version: "" });
  let node = $state({ installed: false, version: "" });
  let npx = $state({ installed: false });

  let installedCount = $derived(
    [homebrew.installed, python.installed, node.installed].filter(Boolean).length
  );

  async function runShell(cmd: string): Promise<{ ok: boolean; stdout: string }> {
    try {
      const command = Command.create("exec-sh", [
        "-c",
        `export PATH="${PATH_PREFIX}:$PATH" && ${cmd}`,
      ]);
      const result = await command.execute();
      return { ok: result.code === 0, stdout: result.stdout.trim() };
    } catch {
      return { ok: false, stdout: "" };
    }
  }

  async function checkAll() {
    checking = true;

    const [brewResult, pythonResult, nodeResult, npxResult] = await Promise.all([
      runShell("brew --version"),
      runShell("python3 --version"),
      runShell("node --version"),
      runShell("which npx"),
    ]);

    homebrew = {
      installed: brewResult.ok,
      version: brewResult.ok ? brewResult.stdout.split("\n")[0].replace("Homebrew ", "") : "",
    };

    python = {
      installed: pythonResult.ok,
      version: pythonResult.ok ? pythonResult.stdout.replace("Python ", "") : "",
    };

    node = {
      installed: nodeResult.ok,
      version: nodeResult.ok ? nodeResult.stdout.replace("v", "") : "",
    };

    npx = {
      installed: npxResult.ok,
    };

    checking = false;

    await onboardingStore.updateDevTools({
      homebrew,
      python,
      node,
      npx,
    });
  }

  onMount(() => {
    checkAll();
  });

  async function openBrewSite() {
    await open("https://brew.sh");
  }

  async function openPythonSite() {
    await open("https://www.python.org/downloads/");
  }

  async function openNodeSite() {
    await open("https://nodejs.org");
  }

  function handleContinue() {
    onNext();
  }
</script>

<div class="flex flex-col px-10 py-8">
  <div class="flex items-center gap-3 mb-3">
    <div class="p-2 bg-primary/10 rounded-lg">
      <Wrench class="w-6 h-6 text-primary" />
    </div>
    <h2 class="text-2xl font-bold text-text">Developer Tools</h2>
    <span class="text-xs bg-primary/10 text-primary px-2 py-1 rounded-full font-medium">
      Optional
    </span>
  </div>

  <p class="text-text-muted mb-6">
    These tools let Son of Simon build apps, run scripts, and perform advanced development tasks
    on your behalf.
  </p>

  <!-- Homebrew -->
  <div class="mb-4">
    {#if homebrew.installed}
      <div class="flex items-start gap-4 p-5 bg-success/10 rounded-xl border border-success/30">
        <div class="w-8 h-8 rounded-full bg-success text-white flex items-center justify-center shrink-0">
          <Check class="w-5 h-5" />
        </div>
        <div class="flex-1">
          <h3 class="font-semibold text-text">Homebrew</h3>
          <p class="text-sm text-text-muted">Installed &mdash; v{homebrew.version}</p>
        </div>
      </div>
    {:else}
      <div class="flex items-start gap-4 p-5 bg-bg-card rounded-xl border border-border">
        <div class="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center font-bold shrink-0">
          1
        </div>
        <div class="flex-1">
          <h3 class="font-semibold text-text mb-1">Homebrew</h3>
          <p class="text-sm text-text-muted mb-3">
            Package manager for macOS. Open Terminal and run:
          </p>
          <code class="block text-xs bg-slate-800 text-slate-200 p-3 rounded-lg mb-3 select-all">
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
          </code>
          <Button variant="secondary" size="sm" onclick={openBrewSite}>
            Open brew.sh
            <ExternalLink class="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>
    {/if}
  </div>

  <!-- Python 3 -->
  <div class="mb-4">
    {#if python.installed}
      <div class="flex items-start gap-4 p-5 bg-success/10 rounded-xl border border-success/30">
        <div class="w-8 h-8 rounded-full bg-success text-white flex items-center justify-center shrink-0">
          <Check class="w-5 h-5" />
        </div>
        <div class="flex-1">
          <h3 class="font-semibold text-text">Python 3</h3>
          <p class="text-sm text-text-muted">Installed &mdash; v{python.version}</p>
        </div>
      </div>
    {:else}
      <div class="flex items-start gap-4 p-5 bg-bg-card rounded-xl border border-border">
        <div class="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center font-bold shrink-0">
          2
        </div>
        <div class="flex-1">
          <h3 class="font-semibold text-text mb-1">Python 3</h3>
          <p class="text-sm text-text-muted mb-3">
            {#if homebrew.installed}
              Install via Homebrew:
              <code class="inline bg-slate-800 text-slate-200 px-2 py-0.5 rounded text-xs">brew install python3</code>
            {:else}
              Download from the official website.
            {/if}
          </p>
          {#if !homebrew.installed}
            <Button variant="secondary" size="sm" onclick={openPythonSite}>
              Open python.org
              <ExternalLink class="w-3.5 h-3.5" />
            </Button>
          {/if}
        </div>
      </div>
    {/if}
  </div>

  <!-- Node.js -->
  <div class="mb-6">
    {#if node.installed}
      <div class="flex items-start gap-4 p-5 bg-success/10 rounded-xl border border-success/30">
        <div class="w-8 h-8 rounded-full bg-success text-white flex items-center justify-center shrink-0">
          <Check class="w-5 h-5" />
        </div>
        <div class="flex-1">
          <h3 class="font-semibold text-text">Node.js</h3>
          <p class="text-sm text-text-muted">
            Installed &mdash; v{node.version}{npx.installed ? " (npx included)" : ""}
          </p>
        </div>
      </div>
    {:else}
      <div class="flex items-start gap-4 p-5 bg-bg-card rounded-xl border border-border">
        <div class="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center font-bold shrink-0">
          3
        </div>
        <div class="flex-1">
          <h3 class="font-semibold text-text mb-1">Node.js</h3>
          <p class="text-sm text-text-muted mb-3">
            {#if homebrew.installed}
              Install via Homebrew:
              <code class="inline bg-slate-800 text-slate-200 px-2 py-0.5 rounded text-xs">brew install node</code>
            {:else}
              Download from the official website.
            {/if}
            <span class="text-text-muted"> npx comes bundled with Node.js.</span>
          </p>
          {#if !homebrew.installed}
            <Button variant="secondary" size="sm" onclick={openNodeSite}>
              Open nodejs.org
              <ExternalLink class="w-3.5 h-3.5" />
            </Button>
          {/if}
        </div>
      </div>
    {/if}
  </div>

  <!-- Recheck button -->
  <div class="flex justify-center mb-6">
    <Button variant="secondary" onclick={checkAll} loading={checking}>
      <RefreshCw class="w-4 h-4" />
      {checking ? "Checking..." : "Recheck All"}
    </Button>
  </div>

  <!-- Info box -->
  <div class="flex items-start gap-3 p-4 bg-bg-card rounded-xl border border-border mb-6">
    <Info class="w-5 h-5 text-primary shrink-0 mt-0.5" />
    <div>
      <p class="text-sm text-text-muted">
        These tools are optional for basic macOS automation but required for building apps
        and advanced development tasks.
      </p>
    </div>
  </div>

  <!-- Navigation -->
  <div class="flex justify-between pt-6 border-t border-border">
    <Button variant="ghost" onclick={onBack}>
      <ArrowLeft class="w-4 h-4" />
      Back
    </Button>
    <Button onclick={handleContinue}>
      Continue
      <ArrowRight class="w-4 h-4" />
    </Button>
  </div>
</div>

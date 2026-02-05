<script lang="ts">
  import { Button, Input } from "$lib/components/ui";
  import { invoke } from "@tauri-apps/api/core";
  import { open } from "@tauri-apps/plugin-shell";
  import { Key, Check, ExternalLink, AlertCircle, ArrowRight, ArrowLeft, Info, CreditCard } from "lucide-svelte";
  import { onboardingStore } from "$lib/stores/onboarding.svelte";

  interface Props {
    onNext: () => void;
    onBack: () => void;
  }

  let { onNext, onBack }: Props = $props();

  let provider = $state(onboardingStore.state.data.api_key.provider);
  let apiKey = $state("");
  let verifying = $state(false);
  let verified = $state(onboardingStore.state.data.api_key.verified);
  let error = $state<string | null>(null);

  const providers = [
    {
      id: "openai",
      name: "OpenAI (GPT-5)",
      description: "The company behind ChatGPT. Widely used and reliable.",
      url: "https://platform.openai.com/api-keys",
      recommended: true,
    },
    {
      id: "anthropic",
      name: "Anthropic (Claude)",
      description: "Powers ChatGPT's competitor Claude. Known for being helpful and safe.",
      url: "https://console.anthropic.com/settings/keys",
      recommended: false,
    },
  ];

  async function openProviderSite() {
    const p = providers.find((p) => p.id === provider);
    if (p) {
      await open(p.url);
    }
  }

  async function verifyKey() {
    if (!apiKey.trim()) {
      error = "Please enter your API key in the field above";
      return;
    }

    verifying = true;
    error = null;

    try {
      // Save API key to config file
      // Use MACBOT_ prefix for pydantic settings, plus standard env var for litellm
      const envVarPrefixed =
        provider === "anthropic" ? "MACBOT_ANTHROPIC_API_KEY" : "MACBOT_OPENAI_API_KEY";
      const envVarStandard =
        provider === "anthropic" ? "ANTHROPIC_API_KEY" : "OPENAI_API_KEY";
      const model =
        provider === "anthropic"
          ? "anthropic/claude-sonnet-4-20250514"
          : "openai/gpt-5.2";

      // Read existing config
      let config = await invoke<string>("read_config");

      // Update or add the API key and model
      const lines = config.split("\n").filter((line) => {
        const trimmed = line.trim();
        return (
          trimmed &&
          !trimmed.startsWith("MACBOT_ANTHROPIC_API_KEY=") &&
          !trimmed.startsWith("MACBOT_OPENAI_API_KEY=") &&
          !trimmed.startsWith("ANTHROPIC_API_KEY=") &&
          !trimmed.startsWith("OPENAI_API_KEY=") &&
          !trimmed.startsWith("MACBOT_MODEL=") &&
          !trimmed.startsWith("MODEL=")
        );
      });

      // Add both prefixed (for pydantic) and standard (for litellm) env vars
      lines.push(`${envVarPrefixed}=${apiKey}`);
      lines.push(`${envVarStandard}=${apiKey}`);
      lines.push(`MACBOT_MODEL=${model}`);

      await invoke("write_config", { content: lines.join("\n") + "\n" });

      // Validate the key format
      const keyPattern =
        provider === "anthropic" ? /^sk-ant-/ : /^sk-[a-zA-Z0-9]/;

      if (!keyPattern.test(apiKey)) {
        error = `This doesn't look like a valid ${provider === "anthropic" ? "Anthropic" : "OpenAI"} API key. It should start with "${provider === "anthropic" ? "sk-ant-" : "sk-"}"`;
        return;
      }

      verified = true;
      await onboardingStore.updateApiKey({
        provider,
        configured: true,
        verified: true,
      });
    } catch (e) {
      error = `Something went wrong: ${e}`;
    } finally {
      verifying = false;
    }
  }

  function handleContinue() {
    if (verified) {
      onNext();
    }
  }
</script>

<div class="flex flex-col px-10 py-8">
  <div class="flex items-center gap-3 mb-3">
    <div class="p-2 bg-primary/10 rounded-lg">
      <Key class="w-6 h-6 text-primary" />
    </div>
    <h2 class="text-2xl font-bold text-text">Connect to AI</h2>
  </div>

  <p class="text-text-muted mb-6">
    Son of Simon uses AI to understand what you want to do. You'll need an API key from an AI provider.
    This is like a password that lets the app talk to the AI service.
  </p>

  <!-- What is an API key? -->
  <div class="flex items-start gap-3 p-4 bg-bg-card rounded-xl border border-border mb-6">
    <Info class="w-5 h-5 text-primary shrink-0 mt-0.5" />
    <div>
      <p class="text-sm text-text-muted">
        <strong class="text-text">What's an API key?</strong> It's a unique code that identifies you to
        the AI service. You'll get one for free when you create an account with Anthropic or OpenAI.
        Usage is pay-as-you-go and typically costs just a few cents per day.
      </p>
    </div>
  </div>

  <!-- Provider Selection -->
  <div class="mb-6">
    <p class="text-sm font-medium text-text mb-3">Choose your AI provider:</p>
    <div class="grid gap-3">
      {#each providers as p}
        <button
          type="button"
          onclick={() => {
            provider = p.id;
            verified = false;
            error = null;
            apiKey = "";
          }}
          class="p-4 rounded-xl border text-left transition-all
                 {provider === p.id
            ? 'border-primary bg-primary/5 ring-2 ring-primary/20'
            : 'border-border bg-bg-card hover:border-text-muted'}"
        >
          <div class="flex items-center justify-between mb-1">
            <span class="font-semibold text-text">{p.name}</span>
            {#if p.recommended}
              <span class="text-xs bg-primary/10 text-primary px-2 py-1 rounded-full font-medium">
                Recommended
              </span>
            {/if}
          </div>
          <p class="text-sm text-text-muted">{p.description}</p>
        </button>
      {/each}
    </div>
  </div>

  {#if !verified}
    <!-- Get API Key Instructions -->
    <div class="mb-6 p-5 bg-bg-card rounded-xl border border-border">
      <h3 class="font-semibold text-text mb-3">How to get your API key:</h3>
      <ol class="text-sm text-text-muted space-y-2 mb-4">
        <li class="flex gap-2">
          <span class="text-primary font-medium">1.</span>
          <span>Click the button below to open {provider === "anthropic" ? "Anthropic" : "OpenAI"}'s website</span>
        </li>
        <li class="flex gap-2">
          <span class="text-primary font-medium">2.</span>
          <span>Create a free account or sign in</span>
        </li>
        <li class="flex gap-2">
          <span class="text-primary font-medium">3.</span>
          <span>Click "Create Key" and copy the key that appears</span>
        </li>
        <li class="flex gap-2">
          <span class="text-primary font-medium">4.</span>
          <span>Paste it in the field below</span>
        </li>
      </ol>
      <Button variant="secondary" onclick={openProviderSite}>
        Open {provider === "anthropic" ? "Anthropic" : "OpenAI"} Website
        <ExternalLink class="w-4 h-4" />
      </Button>
    </div>

    <!-- API Key Input -->
    <div class="mb-6">
      <Input
        type="password"
        label="Paste your API key here"
        placeholder={provider === "anthropic" ? "sk-ant-api03-..." : "sk-proj-..."}
        bind:value={apiKey}
        error={error ?? undefined}
      />
    </div>

    <!-- Save Button -->
    <Button onclick={verifyKey} loading={verifying} disabled={verifying || !apiKey.trim()}>
      {verifying ? "Saving..." : "Save API Key"}
    </Button>
  {:else}
    <!-- Success State -->
    <div class="flex items-center gap-3 p-5 bg-success/10 rounded-xl border border-success/30 mb-6">
      <div class="w-10 h-10 rounded-full bg-success/20 flex items-center justify-center">
        <Check class="w-6 h-6 text-success" />
      </div>
      <div>
        <p class="font-semibold text-success">API key saved successfully!</p>
        <p class="text-sm text-text-muted">Son of Simon is now connected to {provider === "anthropic" ? "Claude" : "GPT-5"}.</p>
      </div>
    </div>
  {/if}

  {#if error}
    <div class="flex items-start gap-3 mt-4 p-4 bg-error/10 rounded-xl border border-error/30">
      <AlertCircle class="w-5 h-5 text-error shrink-0 mt-0.5" />
      <div>
        <p class="font-medium text-error">There was a problem</p>
        <p class="text-sm text-text-muted">{error}</p>
      </div>
    </div>
  {/if}

  <!-- Navigation -->
  <div class="flex justify-between mt-6 pt-6 border-t border-border">
    <Button variant="ghost" onclick={onBack}>
      <ArrowLeft class="w-4 h-4" />
      Back
    </Button>
    <Button onclick={handleContinue} disabled={!verified}>
      Continue
      <ArrowRight class="w-4 h-4" />
    </Button>
  </div>
</div>

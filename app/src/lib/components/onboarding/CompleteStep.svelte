<script lang="ts">
  import { Button } from "$lib/components/ui";
  import { Check, Rocket, PartyPopper } from "lucide-svelte";
  import { onboardingStore } from "$lib/stores/onboarding.svelte";

  interface Props {
    onLaunch: () => void;
  }

  let { onLaunch }: Props = $props();

  let launching = $state(false);

  const summary = $derived([
    {
      label: "AI Provider",
      value:
        onboardingStore.state.data.api_key.provider === "anthropic"
          ? "Claude by Anthropic"
          : "GPT-4 by OpenAI",
      done: onboardingStore.state.data.api_key.configured,
    },
    {
      label: "Remote Control",
      value: onboardingStore.state.data.telegram.configured
        ? "Telegram connected"
        : "Not configured",
      done: onboardingStore.state.data.telegram.configured,
    },
  ]);

  async function handleLaunch() {
    launching = true;
    await onboardingStore.complete();
    onLaunch();
  }
</script>

<div class="flex flex-col items-center text-center px-10 py-8">
  <div
    class="w-24 h-24 bg-success/10 rounded-full flex items-center justify-center mb-6"
  >
    <PartyPopper class="w-12 h-12 text-success" />
  </div>

  <h1 class="text-3xl font-bold text-text mb-3">You're All Set!</h1>

  <p class="text-text-muted mb-8 max-w-lg">
    Son of Simon is ready to help you. Click the button below to open the dashboard,
    where you can start giving commands and see what Son of Simon is doing.
  </p>

  <!-- Summary -->
  <div class="w-full max-w-md mb-8">
    <h3 class="text-sm font-medium text-text mb-3 text-left">Your setup summary:</h3>
    <div class="space-y-3">
      {#each summary as item}
        <div
          class="flex items-center justify-between p-4 bg-bg-card rounded-xl border border-border"
        >
          <span class="text-text-muted">{item.label}</span>
          <div class="flex items-center gap-2">
            <span class="font-medium text-text">{item.value}</span>
            {#if item.done}
              <div class="w-5 h-5 rounded-full bg-success/20 flex items-center justify-center">
                <Check class="w-3 h-3 text-success" />
              </div>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  </div>

  <!-- What happens next -->
  <div class="w-full max-w-md mb-8 p-4 bg-bg-card rounded-xl border border-border text-left">
    <h3 class="font-semibold text-text mb-2">What happens next?</h3>
    <p class="text-sm text-text-muted">
      The dashboard will show you what Son of Simon is doing. You can type commands like
      "check my email" or "what's on my calendar today" and watch it work.
    </p>
  </div>

  <Button size="lg" onclick={handleLaunch} loading={launching}>
    <Rocket class="w-5 h-5" />
    {launching ? "Starting..." : "Open Dashboard"}
  </Button>
</div>

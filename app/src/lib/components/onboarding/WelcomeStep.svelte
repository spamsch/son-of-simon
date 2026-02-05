<script lang="ts">
  import { Button } from "$lib/components/ui";
  import { Sparkles, Terminal, MessageSquare, Calendar, ArrowRight } from "lucide-svelte";

  interface Props {
    onNext: () => void;
  }

  let { onNext }: Props = $props();

  const features = [
    {
      icon: Terminal,
      title: "Talk to Your Mac",
      description: "Just type what you want to do in everyday language. For example: \"Send an email to John about tomorrow's meeting\" or \"Create a reminder to call mom at 5pm\".",
    },
    {
      icon: Calendar,
      title: "Works With Your Apps",
      description: "Son of Simon can control Mail, Calendar, Reminders, Notes, and Safari on your behalf. It reads and creates items just like you would.",
    },
    {
      icon: MessageSquare,
      title: "Control From Anywhere",
      description: "Optionally connect Telegram to send commands to your Mac from your phone, even when you're away from your computer.",
    },
  ];
</script>

<div class="flex flex-col items-center text-center px-10 py-8">
  <div
    class="w-20 h-20 bg-primary/10 rounded-2xl flex items-center justify-center mb-6"
  >
    <Sparkles class="w-10 h-10 text-primary" />
  </div>

  <h1 class="text-3xl font-bold text-text mb-3">Welcome to Son of Simon</h1>

  <p class="text-text-muted mb-8 max-w-lg">
    Your personal AI assistant that helps you automate everyday tasks on your Mac.
    No technical knowledge required.
  </p>

  <div class="grid gap-4 mb-8 w-full max-w-lg text-left">
    {#each features as feature}
      <div
        class="flex items-start gap-4 p-4 bg-bg-card rounded-xl border border-border"
      >
        <div class="p-2 bg-primary/10 rounded-lg shrink-0 mt-0.5">
          <feature.icon class="w-5 h-5 text-primary" />
        </div>
        <div>
          <h3 class="font-semibold text-text mb-1">{feature.title}</h3>
          <p class="text-sm text-text-muted leading-relaxed">{feature.description}</p>
        </div>
      </div>
    {/each}
  </div>

  <div class="space-y-3">
    <Button size="lg" onclick={onNext}>
      Start Setup
      <ArrowRight class="w-5 h-5" />
    </Button>
    <p class="text-xs text-text-muted">
      This will take about 2 minutes to set up
    </p>
  </div>
</div>

<script lang="ts">
  import { X, Download, Copy, CheckCircle } from 'lucide-svelte';

  let {
    xmlContent,
    filename,
    instructions,
    isOpen = $bindable(),
  }: {
    xmlContent: string;
    filename: string;
    instructions: string;
    isOpen: boolean;
  } = $props();

  let copied = $state(false);

  function downloadXml() {
    const blob = new Blob([xmlContent], { type: 'application/xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function copyToClipboard() {
    await navigator.clipboard.writeText(xmlContent);
    copied = true;
    setTimeout(() => copied = false, 2000);
  }
</script>

{#if isOpen}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
    <div class="bg-white rounded-2xl shadow-2xl w-full max-w-5xl max-h-[85vh] flex flex-col">
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-slate-200">
        <div>
          <h2 class="text-sm font-bold text-slate-900">Generated capacity-scheduler.xml</h2>
          <p class="text-[11px] text-slate-500 font-mono mt-0.5">{filename}</p>
        </div>
        <div class="flex items-center gap-2">
          <button onclick={copyToClipboard}
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium hover:bg-slate-50 transition cursor-pointer {copied ? 'text-emerald-600 border-emerald-300' : 'text-slate-700'}">
            {#if copied}
              <CheckCircle class="w-3.5 h-3.5" />
              Copied!
            {:else}
              <Copy class="w-3.5 h-3.5" />
              Copy
            {/if}
          </button>
          <button onclick={downloadXml}
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-sky-600 to-indigo-600 text-white text-xs font-semibold shadow-sm cursor-pointer">
            <Download class="w-3.5 h-3.5" />
            Download
          </button>
          <button onclick={() => isOpen = false} class="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-slate-100 cursor-pointer">
            <X class="w-4 h-4 text-slate-500" />
          </button>
        </div>
      </div>

      <!-- XML Content -->
      <div class="flex-1 overflow-auto p-4">
        <pre class="bg-slate-900 text-slate-100 rounded-xl p-4 text-xs font-mono leading-relaxed overflow-auto max-h-[50vh]">{xmlContent}</pre>
      </div>

      <!-- Instructions -->
      <div class="px-6 py-3 border-t border-slate-200 bg-amber-50">
        <div class="text-[11px] font-semibold text-amber-800 mb-1">Deployment Instructions:</div>
        <pre class="text-[11px] text-amber-700 font-mono whitespace-pre-wrap">{instructions}</pre>
      </div>
    </div>
  </div>
{/if}

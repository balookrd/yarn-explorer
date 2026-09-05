<script lang="ts">
  import type { DiffItem } from '../types';
  import { X, FileDown, Send } from 'lucide-svelte';

  let {
    diffs,
    canAdmin,
    isOpen = $bindable(),
    onGenerateXml,
  }: {
    diffs: DiffItem[];
    canAdmin: boolean;
    isOpen: boolean;
    onGenerateXml: () => void;
  } = $props();

  const changedDiffs = $derived(diffs.filter(d => d.action !== 'unchanged'));

  function actionBadge(action: string): string {
    switch (action) {
      case 'created': return 'bg-emerald-100 text-emerald-700';
      case 'modified': return 'bg-amber-100 text-amber-700';
      case 'deleted': return 'bg-red-100 text-red-700';
      default: return 'bg-slate-100 text-slate-500';
    }
  }
</script>

{#if isOpen}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
    <div class="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[80vh] flex flex-col">
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-slate-200">
        <div>
          <h2 class="text-sm font-bold text-slate-900">Changes Review (Live → Draft)</h2>
          <p class="text-[11px] text-slate-500 mt-0.5">{changedDiffs.length} change(s)</p>
        </div>
        <button onclick={() => isOpen = false} class="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-slate-100 cursor-pointer">
          <X class="w-4 h-4 text-slate-500" />
        </button>
      </div>

      <!-- Table -->
      <div class="flex-1 overflow-auto">
        <table class="w-full text-xs">
          <thead class="bg-slate-50 sticky top-0">
            <tr class="text-[11px] text-slate-500 font-semibold uppercase tracking-wider">
              <th class="text-left px-4 py-2.5">Queue</th>
              <th class="text-center px-2 py-2.5">Action</th>
              <th class="text-right px-2 py-2.5">Capacity</th>
              <th class="text-center px-2 py-2.5"></th>
              <th class="text-right px-2 py-2.5">Draft Capacity</th>
              <th class="text-right px-2 py-2.5">Max Cap</th>
              <th class="text-center px-2 py-2.5"></th>
              <th class="text-right px-2 py-2.5">Draft Max</th>
            </tr>
          </thead>
          <tbody>
            {#each changedDiffs as d}
              <tr class="border-b border-slate-100 hover:bg-slate-50">
                <td class="px-4 py-2 font-mono font-semibold text-slate-800">{d.path}</td>
                <td class="text-center px-2 py-2">
                  <span class="text-[10px] px-2 py-0.5 rounded-full font-bold capitalize {actionBadge(d.action)}">{d.action}</span>
                </td>
                <td class="text-right px-2 py-2 font-mono text-slate-500">
                  {d.live_capacity != null ? `${d.live_capacity.toFixed(1)}%` : '—'}
                </td>
                <td class="text-center px-2 py-2 text-slate-400">→</td>
                <td class="text-right px-2 py-2 font-mono font-bold {
                  d.delta_capacity != null && d.delta_capacity > 0 ? 'text-emerald-600' :
                  d.delta_capacity != null && d.delta_capacity < 0 ? 'text-red-600' : 'text-slate-800'
                }">
                  {d.draft_capacity != null ? `${d.draft_capacity.toFixed(1)}%` : '—'}
                  {#if d.delta_capacity != null && Math.abs(d.delta_capacity) > 0.01}
                    <span class="text-[10px] ml-1">({d.delta_capacity > 0 ? '+' : ''}{d.delta_capacity.toFixed(1)})</span>
                  {/if}
                </td>
                <td class="text-right px-2 py-2 font-mono text-slate-500">
                  {d.live_max_capacity != null ? `${d.live_max_capacity.toFixed(1)}%` : '—'}
                </td>
                <td class="text-center px-2 py-2 text-slate-400">→</td>
                <td class="text-right px-2 py-2 font-mono font-bold {
                  d.delta_max_capacity != null && d.delta_max_capacity > 0 ? 'text-emerald-600' :
                  d.delta_max_capacity != null && d.delta_max_capacity < 0 ? 'text-red-600' : 'text-slate-800'
                }">
                  {d.draft_max_capacity != null ? `${d.draft_max_capacity.toFixed(1)}%` : '—'}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Footer -->
      <div class="flex items-center justify-end gap-2 px-6 py-3 border-t border-slate-200">
        <button onclick={() => isOpen = false}
          class="px-4 py-2 rounded-lg border border-slate-200 text-slate-700 text-xs font-medium hover:bg-slate-50 transition cursor-pointer">
          Close
        </button>
        {#if canAdmin}
          <button onclick={() => { onGenerateXml(); isOpen = false; }}
            class="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gradient-to-r from-sky-600 to-indigo-600 text-white text-xs font-semibold shadow-md cursor-pointer">
            <FileDown class="w-3.5 h-3.5" />
            Generate XML
          </button>
        {:else}
          <button
            class="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-amber-500 text-white text-xs font-semibold shadow-md cursor-pointer"
            title="Send draft for Admin review"
          >
            <Send class="w-3.5 h-3.5" />
            Send for Review
          </button>
        {/if}
      </div>
    </div>
  </div>
{/if}

<script lang="ts">
  import type { BranchBalance } from '../types';
  import { CheckCircle, AlertTriangle, XCircle } from 'lucide-svelte';

  let {
    balances,
    resourceMode,
  }: {
    balances: BranchBalance[];
    resourceMode: string;
  } = $props();
</script>

{#if balances.length > 0}
  <div class="px-4 sm:px-6 py-2 border-b border-slate-200 bg-white">
    <div class="flex items-center gap-3 overflow-x-auto">
      {#each balances as b}
        <div class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs shrink-0 {
          b.is_balanced
            ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
            : b.status === 'overallocated'
              ? 'bg-red-50 border-red-200 text-red-700'
              : 'bg-amber-50 border-amber-200 text-amber-700'
        }">
          {#if b.is_balanced}
            <CheckCircle class="w-3.5 h-3.5" />
          {:else if b.status === 'overallocated'}
            <XCircle class="w-3.5 h-3.5" />
          {:else}
            <AlertTriangle class="w-3.5 h-3.5" />
          {/if}
          <span class="font-mono font-semibold">{b.parent_path}</span>
          <span class="font-medium">
            {b.total_children_capacity.toFixed(1)}%
            {#if !b.is_balanced}
              (headroom: {b.unallocated_capacity.toFixed(1)}%)
            {/if}
          </span>
        </div>
      {/each}
    </div>
  </div>
{/if}

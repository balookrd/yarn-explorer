<script lang="ts">
  import type { DraftQueueItem, PartitionResourceConfig } from '../types';
  import { X, Plus } from 'lucide-svelte';

  let {
    parentPath,
    isOpen = $bindable(),
    resourceMode,
    selectedPartition,
    onConfirm,
  }: {
    parentPath: string;
    isOpen: boolean;
    resourceMode: string;
    selectedPartition: string;
    onConfirm: (draft: DraftQueueItem) => void;
  } = $props();

  let queueName = $state('');
  let capacity = $state(10);
  let maxCapacity = $state(20);
  let queueType = $state<'elastic' | 'fixed'>('elastic');
  let error = $state('');

  function validate(): boolean {
    if (!queueName.trim()) {
      error = 'Queue name is required';
      return false;
    }
    if (!/^[a-z][a-z0-9_]*$/.test(queueName)) {
      error = 'Only lowercase letters, digits, underscore. Must start with a letter.';
      return false;
    }
    if (capacity <= 0 || capacity > 100) {
      error = 'Capacity must be between 0 and 100';
      return false;
    }
    error = '';
    return true;
  }

  function handleTypeChange() {
    if (queueType === 'fixed') {
      maxCapacity = capacity;
    }
  }

  function handleSubmit() {
    if (!validate()) return;

    const actualMaxCap = queueType === 'fixed' ? capacity : maxCapacity;
    const path = `${parentPath}.${queueName}`;

    const part: PartitionResourceConfig = {
      partition_name: selectedPartition,
      capacity,
      max_capacity: actualMaxCap,
      is_elastic: actualMaxCap > capacity,
      elasticity_ratio: capacity > 0 ? Math.round((actualMaxCap / capacity) * 100) / 100 : 1,
    };

    const draft: DraftQueueItem = {
      path,
      name: queueName,
      parent_path: parentPath,
      action: 'create',
      is_leaf: true,
      state: 'RUNNING',
      partitions: { [selectedPartition]: part },
    };

    onConfirm(draft);
    // Reset
    queueName = '';
    capacity = 10;
    maxCapacity = 20;
    queueType = 'elastic';
    error = '';
    isOpen = false;
  }
</script>

{#if isOpen}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
    <div class="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md">
      <div class="flex items-center justify-between mb-5">
        <h2 class="text-sm font-bold text-slate-900">Add New Queue</h2>
        <button onclick={() => isOpen = false} class="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-slate-100 cursor-pointer">
          <X class="w-4 h-4 text-slate-500" />
        </button>
      </div>

      <div class="mb-4 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg">
        <span class="text-[11px] text-slate-500">Parent Queue:</span>
        <span class="text-xs font-mono font-semibold text-slate-800 ml-1">{parentPath}</span>
      </div>

      {#if error}
        <div class="mb-4 p-2.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs">{error}</div>
      {/if}

      <div class="space-y-4">
        <div>
          <label for="new-queue-name" class="block text-xs font-semibold text-slate-700 mb-1.5">Queue Name</label>
          <input
            id="new-queue-name"
            type="text"
            bind:value={queueName}
            placeholder="my_new_queue"
            class="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-sm text-slate-900 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 font-mono"
          />
          <p class="text-[10px] text-slate-400 mt-1">Lowercase letters, digits, underscore only</p>
        </div>

        <div>
          <label for="new-queue-capacity" class="block text-xs font-semibold text-slate-700 mb-1.5">Capacity (%)</label>
          <input
            id="new-queue-capacity"
            type="number"
            bind:value={capacity}
            oninput={handleTypeChange}
            min="0"
            max="100"
            step="0.1"
            class="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-sm font-mono outline-none focus:border-sky-500"
          />
        </div>

        <div>
          <label for="new-queue-type" class="block text-xs font-semibold text-slate-700 mb-1.5">Type</label>
          <select
            id="new-queue-type"
            bind:value={queueType}
            onchange={handleTypeChange}
            class="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-sm outline-none cursor-pointer"
          >
            <option value="elastic">Elastic</option>
            <option value="fixed">Fixed</option>
          </select>
        </div>

        {#if queueType === 'elastic'}
          <div>
            <label for="new-queue-max-capacity" class="block text-xs font-semibold text-slate-700 mb-1.5">Max Capacity (%)</label>
            <input
              id="new-queue-max-capacity"
              type="number"
              bind:value={maxCapacity}
              min={capacity}
              max="100"
              step="0.1"
              class="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-sm font-mono outline-none focus:border-sky-500"
            />
          </div>
        {/if}
      </div>

      <div class="flex items-center gap-2 mt-6">
        <button onclick={() => isOpen = false}
          class="flex-1 py-2 rounded-lg border border-slate-200 text-slate-700 text-xs font-medium hover:bg-slate-50 transition cursor-pointer">
          Cancel
        </button>
        <button onclick={handleSubmit}
          class="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-gradient-to-r from-sky-600 to-indigo-600 text-white text-xs font-semibold shadow-md cursor-pointer">
          <Plus class="w-3.5 h-3.5" />
          Create Queue
        </button>
      </div>
    </div>
  </div>
{/if}

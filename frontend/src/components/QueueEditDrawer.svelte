<script lang="ts">
  import type { QueueNode, DraftQueueItem, PartitionResourceConfig } from '../types';
  import { X, RotateCcw, Save } from 'lucide-svelte';

  let {
    queue,
    draftItem,
    resourceMode,
    selectedPartition,
    isOpen = $bindable(),
    onSave,
  }: {
    queue: QueueNode | null;
    draftItem: DraftQueueItem | null;
    resourceMode: string;
    selectedPartition: string;
    isOpen: boolean;
    onSave: (draft: DraftQueueItem) => void;
  } = $props();

  let editCapacity = $state(0);
  let editMaxCapacity = $state(0);
  let editState = $state<'RUNNING' | 'STOPPED'>('RUNNING');
  let editType = $state<'fixed' | 'elastic'>('elastic');

  // Заполняем поля при открытии
  $effect(() => {
    if (queue && isOpen) {
      const draft = draftItem;
      const part = draft
        ? (draft.partitions[selectedPartition] || draft.partitions['DEFAULT'])
        : (queue.partitions[selectedPartition] || queue.partitions['DEFAULT']);

      if (part) {
        editCapacity = part.capacity;
        editMaxCapacity = part.max_capacity;
        editType = part.is_elastic ? 'elastic' : 'fixed';
      }
      editState = (draft?.state || queue.state) as 'RUNNING' | 'STOPPED';
    }
  });

  function getLivePart(): PartitionResourceConfig | undefined {
    if (!queue) return undefined;
    return queue.partitions[selectedPartition] || queue.partitions['DEFAULT'];
  }

  function handleTypeChange() {
    if (editType === 'fixed') {
      editMaxCapacity = editCapacity;
    }
  }

  function handleCapacityChange() {
    if (editType === 'fixed') {
      editMaxCapacity = editCapacity;
    }
  }

  function handleSave() {
    if (!queue) return;
    const livePart = getLivePart();

    const newPart: PartitionResourceConfig = {
      partition_name: selectedPartition,
      capacity: editCapacity,
      max_capacity: editMaxCapacity,
      is_elastic: editMaxCapacity > editCapacity,
      elasticity_ratio: editCapacity > 0 ? Math.round((editMaxCapacity / editCapacity) * 100) / 100 : 1,
    };

    // Сохраняем все существующие партиции и обновляем текущую
    const existingPartitions = draftItem?.partitions || { ...queue.partitions };
    const updatedPartitions = { ...existingPartitions, [selectedPartition]: newPart };

    const draft: DraftQueueItem = {
      path: queue.path,
      name: queue.name,
      parent_path: queue.parent_path || undefined,
      action: draftItem?.action || 'modify',
      is_leaf: queue.is_leaf,
      state: editState,
      partitions: updatedPartitions,
    };

    onSave(draft);
    isOpen = false;
  }

  function handleReset() {
    if (!queue) return;
    const part = queue.partitions[selectedPartition] || queue.partitions['DEFAULT'];
    if (part) {
      editCapacity = part.capacity;
      editMaxCapacity = part.max_capacity;
      editType = part.is_elastic ? 'elastic' : 'fixed';
    }
    editState = queue.state as 'RUNNING' | 'STOPPED';
  }
</script>

{#if isOpen && queue}
  <!-- Backdrop -->
  <div
    class="fixed inset-0 bg-black/20 z-40"
    onclick={() => isOpen = false}
    role="button"
    tabindex="-1"
    onkeydown={() => {}}
  ></div>

  <!-- Drawer -->
  <div class="fixed right-0 top-0 h-full w-[400px] bg-white border-l border-slate-200 shadow-2xl z-50 flex flex-col">
    <!-- Header -->
    <div class="flex items-center justify-between px-5 py-4 border-b border-slate-200">
      <div>
        <h2 class="text-sm font-bold text-slate-900">Queue Settings</h2>
        <p class="text-[11px] text-slate-500 font-mono mt-0.5">{queue.path}</p>
      </div>
      <button
        onclick={() => isOpen = false}
        class="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-500 transition cursor-pointer"
      >
        <X class="w-4 h-4" />
      </button>
    </div>

    <!-- Form -->
    <div class="flex-1 overflow-auto px-5 py-4 space-y-5">
      <!-- Capacity -->
      <div>
        <label for="edit-queue-capacity" class="block text-xs font-semibold text-slate-700 mb-1.5">
          Capacity (%)
          {#if getLivePart()}
            <span class="text-[10px] text-slate-400 font-normal ml-2">
              Live: {getLivePart()?.capacity.toFixed(1)}%
            </span>
          {/if}
        </label>
        <input
          id="edit-queue-capacity"
          type="number"
          bind:value={editCapacity}
          oninput={handleCapacityChange}
          min="0"
          max="100"
          step="0.1"
          class="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-sm text-slate-900 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 font-mono"
        />
      </div>

      <!-- Type -->
      <div>
        <label for="edit-queue-type" class="block text-xs font-semibold text-slate-700 mb-1.5">Type</label>
        <select
          id="edit-queue-type"
          bind:value={editType}
          onchange={handleTypeChange}
          class="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-sm text-slate-900 outline-none focus:border-sky-500 cursor-pointer"
        >
          <option value="elastic">Elastic (oversubscription allowed)</option>
          <option value="fixed">Fixed (strict limit)</option>
        </select>
      </div>

      <!-- Max Capacity -->
      <div>
        <label for="edit-queue-max-capacity" class="block text-xs font-semibold text-slate-700 mb-1.5">
          Max Capacity (%)
          {#if getLivePart()}
            <span class="text-[10px] text-slate-400 font-normal ml-2">
              Live: {getLivePart()?.max_capacity.toFixed(1)}%
            </span>
          {/if}
        </label>
        <input
          id="edit-queue-max-capacity"
          type="number"
          bind:value={editMaxCapacity}
          min={editCapacity}
          max="100"
          step="0.1"
          disabled={editType === 'fixed'}
          class="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-sm text-slate-900 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 font-mono disabled:opacity-50"
        />
        {#if editType === 'elastic' && editCapacity > 0}
          <p class="text-[10px] text-sky-600 mt-1">
            Elasticity ratio: {(editMaxCapacity / editCapacity).toFixed(2)}x
          </p>
        {/if}
      </div>

      <!-- State -->
      <div>
        <label for="edit-queue-state" class="block text-xs font-semibold text-slate-700 mb-1.5">
          State
          <span class="text-[10px] text-slate-400 font-normal ml-2">Live: {queue.state}</span>
        </label>
        <select
          id="edit-queue-state"
          bind:value={editState}
          class="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-sm text-slate-900 outline-none focus:border-sky-500 cursor-pointer"
        >
          <option value="RUNNING">RUNNING</option>
          <option value="STOPPED">STOPPED</option>
        </select>
      </div>

      <!-- Summary -->
      <div class="bg-slate-50 border border-slate-200 rounded-lg p-3">
        <div class="text-[11px] font-semibold text-slate-500 mb-2">Summary</div>
        <div class="space-y-1 text-xs">
          <div class="flex justify-between"><span class="text-slate-500">Queue:</span><span class="font-mono font-semibold">{queue.name}</span></div>
          <div class="flex justify-between"><span class="text-slate-500">Active Apps:</span><span class="font-semibold">{queue.num_active_applications}</span></div>
          <div class="flex justify-between"><span class="text-slate-500">Pending Apps:</span><span class="font-semibold">{queue.num_pending_applications}</span></div>
          <div class="flex justify-between"><span class="text-slate-500">Used:</span><span class="font-semibold">{queue.current_used_percent.toFixed(1)}%</span></div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="flex items-center gap-2 px-5 py-3 border-t border-slate-200">
      <button
        onclick={handleReset}
        class="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-slate-200 text-slate-700 text-xs font-medium hover:bg-slate-50 transition cursor-pointer"
      >
        <RotateCcw class="w-3.5 h-3.5" />
        Reset to Live
      </button>
      <div class="flex-1"></div>
      <button
        onclick={() => isOpen = false}
        class="px-3 py-2 rounded-lg border border-slate-200 text-slate-700 text-xs font-medium hover:bg-slate-50 transition cursor-pointer"
      >
        Cancel
      </button>
      <button
        onclick={handleSave}
        class="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gradient-to-r from-sky-600 to-indigo-600 text-white text-xs font-semibold shadow-md shadow-sky-500/20 hover:shadow-lg transition cursor-pointer"
      >
        <Save class="w-3.5 h-3.5" />
        Save Changes
      </button>
    </div>
  </div>
{/if}

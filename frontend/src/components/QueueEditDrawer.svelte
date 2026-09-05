<script lang="ts">
  import type { QueueNode, DraftQueueItem, PartitionResourceConfig } from '../types';
  import { X, RotateCcw, Save, HardDrive, Cpu, Link, Unlink, Percent, Hash, AlertCircle } from 'lucide-svelte';
  import { formatMemory, formatVcores, mbToGb, gbToMb } from '../utils/resourceUtils';

  let {
    queue,
    draftItem,
    resourceMode,
    clusterResources = { memory_mb: 2097152, vcores: 1024 },
    selectedPartition,
    isOpen = $bindable(),
    onSave,
  }: {
    queue: QueueNode | null;
    draftItem: DraftQueueItem | null;
    resourceMode: string;
    clusterResources?: { memory_mb: number; vcores: number };
    selectedPartition: string;
    isOpen: boolean;
    onSave: (draft: DraftQueueItem) => void;
  } = $props();

  // Режим ввода: 'percentage' или 'absolute'
  let inputMode = $state<'percentage' | 'absolute'>('percentage');
  let isLinked = $state(true); // Связаны ли RAM и vCPU по долям

  // Поля ввода
  let editRamPercent = $state(0);
  let editRamGb = $state(0);
  let editRamMb = $state(0);

  let editVcorePercent = $state(0);
  let editVcores = $state(0);

  let editMaxRamPercent = $state(0);
  let editMaxRamGb = $state(0);
  let editMaxRamMb = $state(0);

  let editMaxVcorePercent = $state(0);
  let editMaxVcores = $state(0);

  let editState = $state<'RUNNING' | 'STOPPED'>('RUNNING');
  let editType = $state<'fixed' | 'elastic'>('elastic');

  const totalMem = $derived(clusterResources?.memory_mb || 2097152);
  const totalCores = $derived(clusterResources?.vcores || 1024);

  let lastOpenedPath = $state<string | null>(null);

  function parseVal(val: any, fallback = 0): number {
    if (val === '' || val === null || val === undefined) return fallback;
    const n = parseFloat(val);
    return isNaN(n) ? fallback : n;
  }

  function initForm() {
    if (!queue) return;
    const draft = draftItem;
    const part = draft
      ? (draft.partitions[selectedPartition] || draft.partitions['DEFAULT'])
      : (queue.partitions[selectedPartition] || queue.partitions['DEFAULT']);

    if (part) {
      const cap = part.memory_percent ?? part.capacity;
      const vcap = part.vcore_percent ?? part.capacity;
      const maxCap = part.max_memory_percent ?? part.max_capacity;
      const maxVcap = part.max_vcore_percent ?? part.max_capacity;

      editRamPercent = cap;
      editRamMb = part.memory_mb ?? Math.round(totalMem * (cap / 100));
      editRamGb = mbToGb(editRamMb);

      editVcorePercent = vcap;
      editVcores = part.vcores ?? Math.round(totalCores * (vcap / 100));

      editMaxRamPercent = maxCap;
      editMaxRamMb = part.max_memory_mb ?? Math.round(totalMem * (maxCap / 100));
      editMaxRamGb = mbToGb(editMaxRamMb);

      editMaxVcorePercent = maxVcap;
      editMaxVcores = part.max_vcores ?? Math.round(totalCores * (maxVcap / 100));

      editType = part.is_elastic ? 'elastic' : 'fixed';
      isLinked = Math.abs(cap - vcap) < 0.01;
    }
    editState = (draft?.state || queue.state) as 'RUNNING' | 'STOPPED';
  }

  // Заполняем поля только при открытии Drawer или смене очереди
  $effect(() => {
    if (isOpen && queue) {
      if (lastOpenedPath !== queue.path) {
        lastOpenedPath = queue.path;
        initForm();
      }
    } else if (!isOpen) {
      lastOpenedPath = null;
    }
  });

  // Обновление RAM %
  function updateRamPercent(val: number) {
    editRamPercent = val;
    editRamMb = Math.round(totalMem * (val / 100));
    editRamGb = mbToGb(editRamMb);
    if (isLinked) {
      editVcorePercent = val;
      editVcores = Math.round(totalCores * (val / 100));
    }
    if (editType === 'fixed') {
      editMaxRamPercent = editRamPercent;
      editMaxRamMb = editRamMb;
      editMaxRamGb = editRamGb;
      if (isLinked) {
        editMaxVcorePercent = editVcorePercent;
        editMaxVcores = editVcores;
      }
    }
  }

  // Обновление RAM GB
  function updateRamGb(gb: number) {
    editRamGb = gb;
    editRamMb = gbToMb(gb);
    editRamPercent = totalMem > 0 ? Math.round((editRamMb / totalMem) * 1000) / 10 : 0;
    if (isLinked) {
      editVcorePercent = editRamPercent;
      editVcores = Math.round(totalCores * (editVcorePercent / 100));
    }
    if (editType === 'fixed') {
      editMaxRamGb = editRamGb;
      editMaxRamMb = editRamMb;
      editMaxRamPercent = editRamPercent;
      if (isLinked) {
        editMaxVcorePercent = editVcorePercent;
        editMaxVcores = editVcores;
      }
    }
  }

  // Обновление vCPU %
  function updateVcorePercent(val: number) {
    editVcorePercent = val;
    editVcores = Math.round(totalCores * (val / 100));
    if (isLinked) {
      editRamPercent = val;
      editRamMb = Math.round(totalMem * (val / 100));
      editRamGb = mbToGb(editRamMb);
    }
    if (editType === 'fixed') {
      editMaxVcorePercent = editVcorePercent;
      editMaxVcores = editVcores;
      if (isLinked) {
        editMaxRamPercent = editRamPercent;
        editMaxRamMb = editRamMb;
        editMaxRamGb = editRamGb;
      }
    }
  }

  // Обновление vCPU Cores
  function updateVcores(cores: number) {
    editVcores = cores;
    editVcorePercent = totalCores > 0 ? Math.round((cores / totalCores) * 1000) / 10 : 0;
    if (isLinked) {
      editRamPercent = editVcorePercent;
      editRamMb = Math.round(totalMem * (editRamPercent / 100));
      editRamGb = mbToGb(editRamMb);
    }
    if (editType === 'fixed') {
      editMaxVcorePercent = editVcorePercent;
      editMaxVcores = editVcores;
      if (isLinked) {
        editMaxRamPercent = editRamPercent;
        editMaxRamMb = editRamMb;
        editMaxRamGb = editRamGb;
      }
    }
  }

  // Обновление Max RAM %
  function updateMaxRamPercent(val: number) {
    editMaxRamPercent = val;
    editMaxRamMb = Math.round(totalMem * (val / 100));
    editMaxRamGb = mbToGb(editMaxRamMb);
    if (isLinked) {
      editMaxVcorePercent = val;
      editMaxVcores = Math.round(totalCores * (val / 100));
    }
  }

  // Обновление Max RAM GB
  function updateMaxRamGb(gb: number) {
    editMaxRamGb = gb;
    editMaxRamMb = gbToMb(gb);
    editMaxRamPercent = totalMem > 0 ? Math.round((editMaxRamMb / totalMem) * 1000) / 10 : 0;
    if (isLinked) {
      editMaxVcorePercent = editMaxRamPercent;
      editMaxVcores = Math.round(totalCores * (editMaxVcorePercent / 100));
    }
  }

  // Обновление Max vCPU %
  function updateMaxVcorePercent(val: number) {
    editMaxVcorePercent = val;
    editMaxVcores = Math.round(totalCores * (val / 100));
    if (isLinked) {
      editMaxRamPercent = val;
      editMaxRamMb = Math.round(totalMem * (val / 100));
      editMaxRamGb = mbToGb(editMaxRamMb);
    }
  }

  // Обновление Max vCPU Cores
  function updateMaxVcores(cores: number) {
    editMaxVcores = cores;
    editMaxVcorePercent = totalCores > 0 ? Math.round((cores / totalCores) * 1000) / 10 : 0;
    if (isLinked) {
      editMaxRamPercent = editMaxVcorePercent;
      editMaxRamMb = Math.round(totalMem * (editMaxRamPercent / 100));
      editMaxRamGb = mbToGb(editMaxRamMb);
    }
  }

  function handleTypeChange(e: Event) {
    const val = (e.currentTarget as HTMLSelectElement).value as 'fixed' | 'elastic';
    editType = val;
    if (val === 'fixed') {
      editMaxRamPercent = editRamPercent;
      editMaxRamMb = editRamMb;
      editMaxRamGb = editRamGb;
      editMaxVcorePercent = editVcorePercent;
      editMaxVcores = editVcores;
    }
  }

  function handleSave() {
    if (!queue) return;

    const newPart: PartitionResourceConfig = {
      partition_name: selectedPartition,
      capacity: editRamPercent,
      max_capacity: editMaxRamPercent,
      is_elastic: editMaxRamPercent > editRamPercent || editMaxVcorePercent > editVcorePercent,
      elasticity_ratio: editRamPercent > 0 ? Math.round((editMaxRamPercent / editRamPercent) * 100) / 100 : 1,
      memory_mb: editRamMb,
      vcores: editVcores,
      max_memory_mb: editMaxRamMb,
      max_vcores: editMaxVcores,
      memory_percent: editRamPercent,
      vcore_percent: editVcorePercent,
      max_memory_percent: editMaxRamPercent,
      max_vcore_percent: editMaxVcorePercent,
      absolute_resources: {
        memory_mb: editRamMb,
        vcores: editVcores,
      },
      absolute_max_resources: {
        memory_mb: editMaxRamMb,
        vcores: editMaxVcores,
      }
    };

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
      const cap = part.memory_percent ?? part.capacity;
      const vcap = part.vcore_percent ?? part.capacity;
      const maxCap = part.max_memory_percent ?? part.max_capacity;
      const maxVcap = part.max_vcore_percent ?? part.max_capacity;

      editRamPercent = cap;
      editRamMb = part.memory_mb ?? Math.round(totalMem * (cap / 100));
      editRamGb = mbToGb(editRamMb);

      editVcorePercent = vcap;
      editVcores = part.vcores ?? Math.round(totalCores * (vcap / 100));

      editMaxRamPercent = maxCap;
      editMaxRamMb = part.max_memory_mb ?? Math.round(totalMem * (maxCap / 100));
      editMaxRamGb = mbToGb(editMaxRamMb);

      editMaxVcorePercent = maxVcap;
      editMaxVcores = part.max_vcores ?? Math.round(totalCores * (maxVcap / 100));

      editType = part.is_elastic ? 'elastic' : 'fixed';
      isLinked = Math.abs(cap - vcap) < 0.01;
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
  <div class="fixed right-0 top-0 h-full w-[470px] bg-white border-l border-slate-200 shadow-2xl z-50 flex flex-col">
    <!-- Header -->
    <div class="flex items-center justify-between px-5 py-4 border-b border-slate-200 bg-slate-50/50">
      <div>
        <h2 class="text-sm font-bold text-slate-900">Настройки ресурсов очереди</h2>
        <p class="text-[11px] text-slate-500 font-mono mt-0.5">{queue.path}</p>
      </div>
      <button
        onclick={() => isOpen = false}
        class="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-slate-200 text-slate-500 transition cursor-pointer"
      >
        <X class="w-4 h-4" />
      </button>
    </div>

    {#if queue.path === 'root'}
      <div class="px-5 py-2.5 bg-amber-50 border-b border-amber-200 flex items-center gap-2 text-xs text-amber-800">
        <AlertCircle class="w-4 h-4 text-amber-600 shrink-0" />
        <span>Корневая очередь <strong>root</strong> всегда имеет 100% ресурсов кластера. Дочерние очереди делят её ресурсы.</span>
      </div>
    {/if}

    <!-- Mode Switcher & Tools -->
    <div class="px-5 py-2.5 bg-slate-100/60 border-b border-slate-200 flex items-center justify-between">
      <div class="flex items-center gap-1 bg-white p-0.5 rounded-lg border border-slate-200 shadow-xs">
        <button
          onclick={() => inputMode = 'percentage'}
          class="flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold transition cursor-pointer {
            inputMode === 'percentage' ? 'bg-sky-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
          }"
        >
          <Percent class="w-3 h-3" />
          <span>Проценты (%)</span>
        </button>
        <button
          onclick={() => inputMode = 'absolute'}
          class="flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold transition cursor-pointer {
            inputMode === 'absolute' ? 'bg-sky-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
          }"
        >
          <Hash class="w-3 h-3" />
          <span>Абсолютные (GB / CPU)</span>
        </button>
      </div>

      <button
        onclick={() => isLinked = !isLinked}
        title={isLinked ? 'RAM и vCPU синхронизированы (нажмите для раздельного ввода)' : 'RAM и vCPU настраиваются независимо (нажмите для связывания)'}
        class="flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium border transition cursor-pointer {
          isLinked ? 'bg-indigo-50 border-indigo-200 text-indigo-700' : 'bg-slate-100 border-slate-300 text-slate-600'
        }"
      >
        {#if isLinked}
          <Link class="w-3.5 h-3.5 text-indigo-600" />
          <span>Связаны (RAM = vCPU)</span>
        {:else}
          <Unlink class="w-3.5 h-3.5 text-slate-500" />
          <span>Раздельно</span>
        {/if}
      </button>
    </div>

    <!-- Form Body -->
    <div class="flex-1 overflow-auto px-5 py-4 space-y-5">
      
      <!-- Guaranteed Capacity Section -->
      <div class="bg-white border border-slate-200 rounded-xl p-3.5 shadow-xs space-y-3.5">
        <div class="flex items-center justify-between border-b border-slate-100 pb-2">
          <span class="text-xs font-bold text-slate-800 uppercase tracking-wide">Гарантированная емкость (Capacity)</span>
          <span class="text-[10px] text-slate-400">Мин. гарантированная доля</span>
        </div>

        <!-- RAM Guaranteed -->
        <div>
          <div class="flex items-center justify-between text-xs font-semibold text-slate-700 mb-1">
            <span class="flex items-center gap-1 text-indigo-700">
              <HardDrive class="w-3.5 h-3.5" />
              <span>Память (RAM)</span>
            </span>
            <span class="text-[11px] font-mono text-slate-500">
              {#if inputMode === 'percentage'}
                ≈ {editRamGb.toFixed(1)} GB ({editRamMb} MB)
              {:else}
                = {editRamPercent.toFixed(1)}%
              {/if}
            </span>
          </div>

          {#if inputMode === 'percentage'}
            <div class="relative">
              <input
                type="number"
                value={editRamPercent}
                oninput={(e) => updateRamPercent(parseVal(e.currentTarget.value, 0))}
                min="0"
                max="100"
                step="0.1"
                class="w-full px-3 py-1.5 rounded-lg border border-slate-300 bg-white text-sm font-mono text-slate-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
              />
              <span class="absolute right-3 top-2 text-xs font-bold text-slate-400">%</span>
            </div>
          {:else}
            <div class="relative">
              <input
                type="number"
                value={editRamGb}
                oninput={(e) => updateRamGb(parseVal(e.currentTarget.value, 0))}
                min="0"
                max={mbToGb(totalMem)}
                step="1"
                class="w-full px-3 py-1.5 rounded-lg border border-slate-300 bg-white text-sm font-mono text-slate-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
              />
              <span class="absolute right-3 top-2 text-xs font-bold text-slate-400">GB</span>
            </div>
          {/if}
        </div>

        <!-- vCPU Guaranteed -->
        <div>
          <div class="flex items-center justify-between text-xs font-semibold text-slate-700 mb-1">
            <span class="flex items-center gap-1 text-blue-700">
              <Cpu class="w-3.5 h-3.5" />
              <span>Процессор (vCPU)</span>
              {#if isLinked}
                <span class="text-[10px] text-indigo-500 font-normal">(синхронизируется с RAM)</span>
              {/if}
            </span>
            <span class="text-[11px] font-mono text-slate-500">
              {#if inputMode === 'percentage'}
                ≈ {editVcores} Cores
              {:else}
                = {editVcorePercent.toFixed(1)}%
              {/if}
            </span>
          </div>

          {#if inputMode === 'percentage'}
            <div class="relative">
              <input
                type="number"
                value={editVcorePercent}
                oninput={(e) => updateVcorePercent(parseVal(e.currentTarget.value, 0))}
                min="0"
                max="100"
                step="0.1"
                class="w-full px-3 py-1.5 rounded-lg border border-slate-300 bg-white text-sm font-mono text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
              />
              <span class="absolute right-3 top-2 text-xs font-bold text-slate-400">%</span>
            </div>
          {:else}
            <div class="relative">
              <input
                type="number"
                value={editVcores}
                oninput={(e) => updateVcores(parseVal(e.currentTarget.value, 0))}
                min="0"
                max={totalCores}
                step="1"
                class="w-full px-3 py-1.5 rounded-lg border border-slate-300 bg-white text-sm font-mono text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
              />
              <span class="absolute right-3 top-2 text-xs font-bold text-slate-400">Cores</span>
            </div>
          {/if}
        </div>
      </div>

      <!-- Max Capacity (Burst Limit) -->
      <div class="bg-white border border-slate-200 rounded-xl p-3.5 shadow-xs space-y-3.5">
        <div class="flex items-center justify-between border-b border-slate-100 pb-2">
          <div class="flex items-center gap-2">
            <span class="text-xs font-bold text-slate-800 uppercase tracking-wide">Макс. лимит (Max Capacity)</span>
            <select
              value={editType}
              onchange={handleTypeChange}
              class="px-2 py-0.5 rounded text-[11px] font-semibold border border-slate-300 bg-slate-50 cursor-pointer"
            >
              <option value="elastic">Elastic (разрешить burst)</option>
              <option value="fixed">Fixed (строго = capacity)</option>
            </select>
          </div>
        </div>

        {#if editType === 'elastic'}
          <!-- Max RAM -->
          <div>
            <div class="flex items-center justify-between text-xs font-semibold text-slate-700 mb-1">
              <span class="flex items-center gap-1 text-indigo-700">
                <HardDrive class="w-3.5 h-3.5" />
                <span>Max RAM</span>
              </span>
              <span class="text-[11px] font-mono text-slate-500">
                {#if inputMode === 'percentage'}
                  ≈ {editMaxRamGb.toFixed(1)} GB
                {:else}
                  = {editMaxRamPercent.toFixed(1)}%
                {/if}
              </span>
            </div>

            {#if inputMode === 'percentage'}
              <div class="relative">
                <input
                  type="number"
                  value={editMaxRamPercent}
                  oninput={(e) => updateMaxRamPercent(parseVal(e.currentTarget.value, 0))}
                  min={editRamPercent}
                  max="100"
                  step="0.1"
                  class="w-full px-3 py-1.5 rounded-lg border border-slate-300 bg-white text-sm font-mono text-slate-900 outline-none focus:border-indigo-500"
                />
                <span class="absolute right-3 top-2 text-xs font-bold text-slate-400">%</span>
              </div>
            {:else}
              <div class="relative">
                <input
                  type="number"
                  value={editMaxRamGb}
                  oninput={(e) => updateMaxRamGb(parseVal(e.currentTarget.value, 0))}
                  min={editRamGb}
                  max={mbToGb(totalMem)}
                  step="1"
                  class="w-full px-3 py-1.5 rounded-lg border border-slate-300 bg-white text-sm font-mono text-slate-900 outline-none focus:border-indigo-500"
                />
                <span class="absolute right-3 top-2 text-xs font-bold text-slate-400">GB</span>
              </div>
            {/if}
          </div>

          <!-- Max vCPU -->
          <div>
            <div class="flex items-center justify-between text-xs font-semibold text-slate-700 mb-1">
              <span class="flex items-center gap-1 text-blue-700">
                <Cpu class="w-3.5 h-3.5" />
                <span>Max vCPU</span>
                {#if isLinked}
                  <span class="text-[10px] text-indigo-500 font-normal">(синхронизируется с RAM)</span>
                {/if}
              </span>
              <span class="text-[11px] font-mono text-slate-500">
                {#if inputMode === 'percentage'}
                  ≈ {editMaxVcores} Cores
                {:else}
                  = {editMaxVcorePercent.toFixed(1)}%
                {/if}
              </span>
            </div>

            {#if inputMode === 'percentage'}
              <div class="relative">
                <input
                  type="number"
                  value={editMaxVcorePercent}
                  oninput={(e) => updateMaxVcorePercent(parseVal(e.currentTarget.value, 0))}
                  min={editVcorePercent}
                  max="100"
                  step="0.1"
                  class="w-full px-3 py-1.5 rounded-lg border border-slate-300 bg-white text-sm font-mono text-slate-900 outline-none focus:border-blue-500"
                />
                <span class="absolute right-3 top-2 text-xs font-bold text-slate-400">%</span>
              </div>
            {:else}
              <div class="relative">
                <input
                  type="number"
                  value={editMaxVcores}
                  oninput={(e) => updateMaxVcores(parseVal(e.currentTarget.value, 0))}
                  min={editVcores}
                  max={totalCores}
                  step="1"
                  class="w-full px-3 py-1.5 rounded-lg border border-slate-300 bg-white text-sm font-mono text-slate-900 outline-none focus:border-blue-500"
                />
                <span class="absolute right-3 top-2 text-xs font-bold text-slate-400">Cores</span>
              </div>
            {/if}
          </div>

          {#if editRamPercent > 0}
            <div class="bg-sky-50 border border-sky-100 rounded-lg p-2 text-[11px] text-sky-800 flex justify-between">
              <span>Коэффициент эластичности RAM:</span>
              <span class="font-bold">{(editMaxRamPercent / editRamPercent).toFixed(2)}x</span>
            </div>
          {/if}
        {:else}
          <div class="text-xs text-slate-500 italic p-2 bg-slate-50 rounded border border-slate-100">
            Очередь работает в фиксированном режиме. Потребление жестко ограничено гарантированной емкостью.
          </div>
        {/if}
      </div>

      <!-- State -->
      <div>
        <label for="edit-queue-state" class="block text-xs font-semibold text-slate-700 mb-1.5">
          Состояние очереди (State)
        </label>
        <select
          id="edit-queue-state"
          bind:value={editState}
          class="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-sm text-slate-900 outline-none focus:border-sky-500 cursor-pointer"
        >
          <option value="RUNNING">RUNNING (активна)</option>
          <option value="STOPPED">STOPPED (остановлена)</option>
        </select>
      </div>

      <!-- Summary -->
      <div class="bg-slate-50 border border-slate-200 rounded-lg p-3">
        <div class="text-[11px] font-semibold text-slate-500 mb-2 uppercase">Кластерные ресурсы</div>
        <div class="space-y-1 text-xs">
          <div class="flex justify-between"><span class="text-slate-500">Всего RAM в кластере:</span><span class="font-mono font-semibold">{formatMemory(totalMem)}</span></div>
          <div class="flex justify-between"><span class="text-slate-500">Всего vCPU в кластере:</span><span class="font-mono font-semibold">{formatVcores(totalCores)}</span></div>
          <div class="flex justify-between"><span class="text-slate-500">Текущие приложения:</span><span class="font-semibold">{queue.num_active_applications} акт. / {queue.num_pending_applications} в оч.</span></div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="flex items-center gap-2 px-5 py-3 border-t border-slate-200 bg-slate-50/50">
      <button
        onclick={handleReset}
        class="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-slate-200 text-slate-700 text-xs font-medium hover:bg-white transition cursor-pointer"
      >
        <RotateCcw class="w-3.5 h-3.5" />
        Сбросить к live
      </button>
      <div class="flex-1"></div>
      <button
        onclick={() => isOpen = false}
        class="px-3 py-2 rounded-lg border border-slate-200 text-slate-700 text-xs font-medium hover:bg-white transition cursor-pointer"
      >
        Отмена
      </button>
      <button
        onclick={handleSave}
        class="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gradient-to-r from-sky-600 to-indigo-600 text-white text-xs font-semibold shadow-md shadow-sky-500/20 hover:shadow-lg transition cursor-pointer"
      >
        <Save class="w-3.5 h-3.5" />
        Сохранить в черновик
      </button>
    </div>
  </div>
{/if}

<script lang="ts">
  import { Lock, User } from 'lucide-svelte';

  let {
    onLogin
  }: {
    onLogin: (username: string, password: string) => Promise<void>;
  } = $props();

  let username = $state('');
  let password = $state('');
  let isLoading = $state(false);
  let errorMessage = $state('');

  async function handleSubmit(e: Event) {
    e.preventDefault();
    if (!username.trim() || !password.trim()) return;
    isLoading = true;
    errorMessage = '';
    try {
      await onLogin(username, password);
    } catch (err: any) {
      errorMessage = err.message || 'Ошибка авторизации';
    } finally {
      isLoading = false;
    }
  }
</script>

<div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
  <div class="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-sm">
    <!-- Logo -->
    <div class="flex flex-col items-center mb-6">
      <div class="w-14 h-14 rounded-2xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-sky-500/30 mb-3">
        <Lock class="w-7 h-7" />
      </div>
      <h1 class="text-xl font-bold text-slate-900">YARN Queue Explorer</h1>
      <p class="text-xs text-slate-500 mt-1">Авторизация через LDAP / Kerberos</p>
    </div>

    <form onsubmit={handleSubmit}>
      {#if errorMessage}
        <div class="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs font-medium">
          {errorMessage}
        </div>
      {/if}

      <div class="mb-4">
        <label for="username" class="block text-xs font-semibold text-slate-700 mb-1.5">
          Имя пользователя
        </label>
        <div class="relative">
          <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
            <User class="w-4 h-4" />
          </span>
          <input
            id="username"
            type="text"
            bind:value={username}
            placeholder="username"
            class="w-full pl-10 pr-3 py-2.5 rounded-lg border border-slate-200 bg-slate-50 text-sm text-slate-900 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 transition"
            disabled={isLoading}
          />
        </div>
      </div>

      <div class="mb-6">
        <label for="password" class="block text-xs font-semibold text-slate-700 mb-1.5">
          Пароль
        </label>
        <div class="relative">
          <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
            <Lock class="w-4 h-4" />
          </span>
          <input
            id="password"
            type="password"
            bind:value={password}
            placeholder="••••••••"
            class="w-full pl-10 pr-3 py-2.5 rounded-lg border border-slate-200 bg-slate-50 text-sm text-slate-900 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 transition"
            disabled={isLoading}
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={isLoading || !username.trim() || !password.trim()}
        class="w-full py-2.5 rounded-lg bg-gradient-to-r from-sky-600 to-indigo-600 text-white text-sm font-semibold shadow-md shadow-sky-500/20 hover:shadow-lg hover:shadow-sky-500/30 transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
      >
        {#if isLoading}
          <span class="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2"></span>
        {/if}
        Войти в систему
      </button>
    </form>
  </div>
</div>

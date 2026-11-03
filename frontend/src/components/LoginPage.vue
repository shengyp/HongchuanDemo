<script setup lang="ts">
import { computed, ref } from 'vue'
import { api } from '../api'
import type { User } from '../types'

const emit = defineEmits<{ authenticated: [user: User] }>()
const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const showPassword = ref(false)
const busy = ref(false)
const error = ref('')
const heading = computed(() => mode.value === 'login' ? '欢迎回来' : '创建账号')

function switchMode(next: 'login' | 'register'): void {
  mode.value = next
  error.value = ''
  password.value = ''
}

async function submit(): Promise<void> {
  error.value = ''
  const account = username.value.trim()
  if (!/^[A-Za-z][A-Za-z0-9_]{2,31}$/.test(account)) {
    error.value = '账号须为 3–32 位，以字母开头，只能使用字母、数字和下划线。'
    return
  }
  if (mode.value === 'register' && (password.value.length < 8 || password.value.length > 128)) {
    error.value = '密码长度须为 8–128 个字符。'
    return
  }
  if (!password.value) {
    error.value = '请输入密码。'
    return
  }
  busy.value = true
  try {
    const user = mode.value === 'login'
      ? await api.login(account, password.value)
      : await api.register(account, password.value)
    password.value = ''
    emit('authenticated', user)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '操作失败，请稍后重试。'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <div class="login-shell">
      <div class="login-brand" aria-label="NutriGraph 营养食谱研究平台">
        <span class="login-brand-mark">✦</span>
        <span><strong>NutriGraph</strong><small>营养食谱研究平台</small></span>
      </div>

      <div class="login-grid">
        <section class="login-intro" aria-labelledby="login-intro-title">
          <div class="login-intro-copy">
            <span class="login-kicker">营养食谱研究平台</span>
            <h1 id="login-intro-title">让每一餐，<br><span>更有依据。</span></h1>
            <p>整理食材与食谱数据，探索搭配关系，查看营养结果。登录后继续你的研究与对话。</p>
          </div>
          <div class="login-feature-list" aria-label="平台功能">
            <span><i class="mdi mdi-database-outline" aria-hidden="true"></i> 食谱数据</span>
            <span><i class="mdi mdi-graph-outline" aria-hidden="true"></i> 食材关联</span>
            <span><i class="mdi mdi-chat-outline" aria-hidden="true"></i> 营养问答</span>
          </div>
          <div class="login-art" aria-hidden="true">
            <span class="login-orbit login-orbit-one"></span>
            <span class="login-orbit login-orbit-two"></span>
            <span class="login-art-center">✦</span>
            <span class="login-art-node login-art-node-a"></span>
            <span class="login-art-node login-art-node-b"></span>
            <span class="login-art-node login-art-node-c"></span>
          </div>
        </section>

        <section class="login-form-panel" aria-labelledby="login-heading">
          <div class="login-form-wrap">
            <div class="login-overline">NUTRIGRAPH ACCOUNT</div>
            <h2 id="login-heading">{{ heading }}</h2>
            <p class="login-subtitle">{{ mode === 'login' ? '登录账号，继续使用你的营养食谱工作台。' : '创建账号，保存你的对话记录。' }}</p>

            <div class="login-switch" role="group" aria-label="账号操作">
              <button type="button" :class="{ active: mode === 'login' }" :aria-pressed="mode === 'login'" @click="switchMode('login')">登录</button>
              <button type="button" :class="{ active: mode === 'register' }" :aria-pressed="mode === 'register'" @click="switchMode('register')">注册</button>
            </div>

            <form class="login-form" @submit.prevent="submit">
              <label for="login-username">账号</label>
              <input id="login-username" v-model="username" name="username" type="text" autocomplete="username" placeholder="请输入账号" maxlength="32" required />
              <p v-if="mode === 'register'" class="login-field-hint">3–32 位，以字母开头，可使用字母、数字和下划线</p>

              <label for="login-password">密码</label>
              <div class="login-password-field">
                <input id="login-password" v-model="password" name="password" :type="showPassword ? 'text' : 'password'" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" placeholder="请输入密码" required />
                <button type="button" :aria-label="showPassword ? '隐藏密码' : '显示密码'" @click="showPassword = !showPassword"><i :class="showPassword ? 'mdi mdi-eye-off-outline' : 'mdi mdi-eye-outline'" aria-hidden="true"></i></button>
              </div>
              <p v-if="mode === 'register'" class="login-field-hint">密码至少 8 位</p>

              <p v-if="error" class="login-error" role="alert">{{ error }}</p>
              <button class="login-submit" type="submit" :disabled="busy">{{ busy ? '请稍候…' : (mode === 'login' ? '登录工作台' : '创建账号并进入') }} <i class="mdi mdi-arrow-right" aria-hidden="true"></i></button>
            </form>
            <p class="login-footnote">账号用于保存你的对话记录。</p>
          </div>
        </section>
      </div>
      <footer class="login-footer">NutriGraph · 营养食谱研究平台</footer>
    </div>
  </main>
</template>

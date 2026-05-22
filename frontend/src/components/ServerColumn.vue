<template>
  <div class="panel column">
    <div class="panel-title">
      <span class="dot" :class="stats?.online ? 'online-dot' : 'offline-dot'"></span>
      {{ serverName }} (.{{ ipSuffix }})
      <span v-if="stats && !stats.online" class="offline-tag">离线</span>
      <button v-if="isDynamic" @click="$emit('remove')" class="btn-remove" title="移除主机">✕</button>
    </div>
    <div class="stats-cards">
      <div class="stat-card"><div class="stat-ring"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="50" class="bg-ring"/><circle cx="60" cy="60" r="50" class="color-ring cpu" :style="{ strokeDasharray: (stats?.cpu || 0) * 3.14 + ' 314' }"/></svg><div class="stat-value">{{ stats?.cpu || 0 }}%</div></div><div class="stat-label">CPU</div></div>
      <div class="stat-card"><div class="stat-ring"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="50" class="bg-ring"/><circle cx="60" cy="60" r="50" class="color-ring mem" :style="{ strokeDasharray: (stats?.memory || 0) * 3.14 + ' 314' }"/></svg><div class="stat-value">{{ stats?.memory || 0 }}%</div></div><div class="stat-label">内存</div></div>
      <div class="stat-card"><div class="stat-ring"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="50" class="bg-ring"/><circle cx="60" cy="60" r="50" class="color-ring disk" :style="{ strokeDasharray: (stats?.disk || 0) * 3.14 + ' 314' }"/></svg><div class="stat-value">{{ stats?.disk || 0 }}%</div></div><div class="stat-label">磁盘</div></div>
    </div>
    <div class="command-center">
      <div class="cmd-label">⌨️ 点击输入框查看命令，回车执行</div>
      <div class="cmd-input-wrapper">
        <input :value="cmd" @input="$emit('update:cmd', $event.target.value)" placeholder="输入命令..." 
          @focus="showSuggest[serverId] = true"
          @keyup.enter="$emit('run')"
          @keydown.down.prevent="moveDown"
          @keydown.up.prevent="moveUp"
          class="cmd-input-center" />
        <button @click="$emit('run')" class="btn-exec-center">▶</button>
      </div>
      <div v-show="showSuggest[serverId]" class="suggest-box">
        <div class="suggest-title">可用命令：</div>
        <div v-for="(item, idx) in filteredCmds" :key="item.cmd"
          :class="['suggest-item', { active: suggestIdx[serverId] === idx }]"
          @mousedown.prevent="selectCmd(item.cmd)"
          @mouseenter="suggestIdx[serverId] = idx">
          <code>{{ item.cmd }}</code>
          <span>{{ item.desc }}</span>
        </div>
      </div>
      <div v-if="results[serverId]" class="result-box-center">
        <div class="result-header-center"><span>执行结果</span><button @click="results[serverId] = ''" class="btn-close-center">✕</button></div>
        <pre>{{ results[serverId] }}</pre>
      </div>
      <div v-if="loading[serverId]" class="loading-center">⚡ 执行中...</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  serverId: String,
  stats: Object,
  cmd: String,
  results: Object,
  loading: Object,
  allCommands: Array,
  showSuggest: Object,
  suggestIdx: Object
})

const emit = defineEmits(['update:cmd', 'run', 'remove'])

const isDynamic = computed(() => {
  return props.serverId !== 'server-138' && props.serverId !== 'server-139'
})

const serverName = computed(() => {
  const names = { 'server-138': 'Web服务器', 'server-139': '数据库服务器' }
  return names[props.serverId] || props.serverId.replace('server-', '服务器 ')
})
const ipSuffix = computed(() => {
  const ips = { 'server-138': '138', 'server-139': '139' }
  return ips[props.serverId] || props.serverId.replace('server-', '').replace(/-/g, '.')
})

const filteredCmds = computed(() => {
  if (!props.allCommands) return []
  const q = (props.cmd || '').toLowerCase().trim()
  if (!q) return props.allCommands
  return props.allCommands.filter(c => c.cmd.toLowerCase().includes(q) || c.desc.includes(q))
})

const moveDown = () => {
  if (props.suggestIdx[props.serverId] < filteredCmds.value.length - 1) {
    props.suggestIdx[props.serverId]++
  }
}
const moveUp = () => {
  if (props.suggestIdx[props.serverId] > 0) {
    props.suggestIdx[props.serverId]--
  }
}
const selectCmd = (cmd) => {
  emit('update:cmd', cmd)
  props.showSuggest[props.serverId] = false
  emit('run')
}
</script>

<style scoped>
.column { flex: 1; min-width: 260px; background: rgba(10, 25, 55, 0.8); border: 1px solid #1a3a6a; border-radius: 8px; padding: 10px; overflow-y: auto; display: flex; flex-direction: column; }
.panel-title { font-size: 14px; color: #4fd2f1; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }
.dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.online-dot { background: #4fd2f1; box-shadow: 0 0 5px #4fd2f1; }
.offline-dot { background: #e65d5d; }
.offline-tag { font-size: 10px; color: #e65d5d; background: rgba(230,93,93,0.15); padding: 1px 5px; border-radius: 3px; }
.btn-remove { margin-left: auto; background: rgba(230,93,93,0.2); border: 1px solid #e65d5d; color: #e65d5d; width: 20px; height: 20px; border-radius: 50%; cursor: pointer; font-size: 11px; display: flex; align-items: center; justify-content: center; }
.btn-remove:hover { background: rgba(230,93,93,0.5); }

.stats-cards { display: flex; gap: 6px; margin-bottom: 8px; }
.stat-card { flex: 1; text-align: center; padding: 4px; background: rgba(0,0,0,0.2); border-radius: 6px; }
.stat-ring { position: relative; width: 65px; height: 65px; margin: 0 auto; }
.stat-ring svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.bg-ring { fill: none; stroke: #1a2a4a; stroke-width: 5; }
.color-ring { fill: none; stroke-width: 5; stroke-linecap: round; transition: stroke-dasharray 0.5s; }
.color-ring.cpu { stroke: #00d4ff; }
.color-ring.mem { stroke: #f6dd0e; }
.color-ring.disk { stroke: #e65d5d; }
.stat-value { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 14px; font-weight: bold; }
.stat-label { font-size: 10px; color: #6b9bd6; margin-top: 3px; }

.command-center { flex: 1; display: flex; flex-direction: column; min-height: 150px; position: relative; }
.cmd-label { font-size: 10px; color: #6b9bd6; margin-bottom: 5px; }
.cmd-input-wrapper { display: flex; gap: 4px; position: relative; z-index: 10; }
.cmd-input-center { flex: 1; background: rgba(0,0,0,0.4); border: 1px solid #2a5a8a; color: #e0e8f0; padding: 6px 10px; border-radius: 5px; font-size: 12px; outline: none; }
.cmd-input-center:focus { border-color: #4fd2f1; }
.cmd-input-center::placeholder { color: #3a5a8a; font-size: 10px; }
.btn-exec-center { background: #4fd2f1; border: none; color: #0a1a2f; padding: 6px 12px; border-radius: 5px; cursor: pointer; font-size: 12px; font-weight: bold; }

.suggest-box { background: #0d1f4a; border: 1px solid #2a5a8a; border-radius: 5px; max-height: 200px; overflow-y: auto; margin-top: 3px; box-shadow: 0 4px 15px rgba(0,0,0,0.6); z-index: 5; }
.suggest-title { font-size: 9px; color: #4fd2f1; padding: 4px 8px 3px; border-bottom: 1px solid #1a2a4a; }
.suggest-item { display: flex; align-items: center; gap: 6px; padding: 4px 8px; cursor: pointer; border-bottom: 1px solid #1a2a4a; font-size: 11px; }
.suggest-item.active { background: rgba(79,210,241,0.15); }
.suggest-item:hover { background: rgba(79,210,241,0.1); }
.suggest-item code { color: #adff2f; font-size: 10px; background: rgba(0,0,0,0.3); padding: 1px 5px; border-radius: 3px; white-space: nowrap; }
.suggest-item span { color: #6b9bd6; font-size: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.result-box-center { margin-top: 6px; background: #0a0f1a; border: 1px solid #1a3a6a; border-radius: 4px; max-height: 180px; overflow: auto; flex: 1; }
.result-header-center { display: flex; justify-content: space-between; align-items: center; padding: 3px 6px; background: #111a2a; font-size: 10px; color: #6b9bd6; position: sticky; top: 0; }
.btn-close-center { background: none; border: none; color: #e65d5d; cursor: pointer; font-size: 12px; }
.result-box-center pre { padding: 4px 6px; font-size: 9px; color: #adff2f; white-space: pre-wrap; word-break: break-all; margin: 0; }
.loading-center { text-align: center; color: #f6dd0e; font-size: 11px; padding: 6px; }

.column::-webkit-scrollbar, .result-box-center::-webkit-scrollbar, .suggest-box::-webkit-scrollbar { width: 3px; }
.column::-webkit-scrollbar-thumb, .result-box-center::-webkit-scrollbar-thumb, .suggest-box::-webkit-scrollbar-thumb { background: #2a4a7a; border-radius: 2px; }
</style>

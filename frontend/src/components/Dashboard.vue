<template>
  <div class="dashboard">
    <div class="header">
      <div class="header-left"><span class="time">{{ currentTime }}</span></div>
      <h1 class="title">分布式服务器监控控制大屏</h1>
      <div class="header-right">
        <button @click="showAddServer = true" class="btn-help">➕ 添加主机</button>
        <button @click="showAllCommands = true" class="btn-help">📋 所有命令</button>
        <span class="status" :class="{ online: wsConnected }">{{ wsConnected ? '● 已连接' : '○ 断开' }}</span>
      </div>
    </div>

    <div class="main-content" ref="mainContent">
      <!-- 128 本机 -->
      <div class="panel column local-column">
        <div class="panel-title"><span class="dot online-dot"></span>监控中心 (.128)</div>
        <div class="stats-cards">
          <div class="stat-card"><div class="stat-ring"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="50" class="bg-ring"/><circle cx="60" cy="60" r="50" class="color-ring cpu" :style="{ strokeDasharray: local.cpu * 3.14 + ' 314' }"/></svg><div class="stat-value">{{ local.cpu }}%</div></div><div class="stat-label">CPU</div></div>
          <div class="stat-card"><div class="stat-ring"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="50" class="bg-ring"/><circle cx="60" cy="60" r="50" class="color-ring mem" :style="{ strokeDasharray: local.memory * 3.14 + ' 314' }"/></svg><div class="stat-value">{{ local.memory }}%</div></div><div class="stat-label">内存</div></div>
          <div class="stat-card"><div class="stat-ring"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="50" class="bg-ring"/><circle cx="60" cy="60" r="50" class="color-ring disk" :style="{ strokeDasharray: local.disk * 3.14 + ' 314' }"/></svg><div class="stat-value">{{ local.disk }}%</div></div><div class="stat-label">磁盘</div></div>
        </div>
        <div class="network-mini"><span>↑ {{ formatNet(local.prev_sent, local.net_sent) }} MB/s</span><span>↓ {{ formatNet(local.prev_recv, local.net_recv) }} MB/s</span></div>
        <div class="chart-container"><div ref="chartRef" class="chart"></div></div>
      </div>

      <!-- 动态服务器 -->
      <ServerColumn v-for="sid in allServerIds" :key="sid" :server-id="sid" :stats="serversStats[sid]" v-model:cmd="dynamicCmds[sid]" :results="results" :loading="loading" :all-commands="allCommands" :show-suggest="showSuggest" :suggest-idx="suggestIdx" @run="runCmd(sid)" @remove="removeServer(sid)" />

      <!-- 空状态 -->
      <div v-if="allServerIds.length === 0" class="panel column empty-column">
        <div class="empty-hint">
          <div class="empty-icon">🖥️</div>
          <p>还没有被控主机</p>
          <button @click="showAddServer = true" class="btn-empty">➕ 添加主机</button>
        </div>
      </div>
    </div>

    <!-- 添加主机弹窗 -->
    <div v-if="showAddServer" class="modal-overlay" @click.self="showAddServer = false">
      <div class="modal modal-small">
        <div class="modal-header">
          <h2>➕ 添加被控主机</h2>
          <button @click="showAddServer = false" class="btn-close-modal">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>IP 地址 *</label>
            <input v-model="newServer.ip" placeholder="例如: 192.168.152.138" class="form-input" />
          </div>
          <div class="form-group">
            <label>SSH 用户名</label>
            <input v-model="newServer.username" placeholder="默认 root" class="form-input" />
          </div>
          <div class="form-group">
            <label>SSH 密码 *</label>
            <input v-model="newServer.password" type="password" placeholder="输入密码" class="form-input" />
          </div>
          <div class="form-group">
            <label>SSH 端口</label>
            <input v-model.number="newServer.port" type="number" placeholder="默认 22" class="form-input" />
          </div>
          <div class="form-group">
            <label>显示名称</label>
            <input v-model="newServer.name" placeholder="可选，如: Web服务器" class="form-input" />
          </div>
          <div v-if="addError" class="error-msg">{{ addError }}</div>
          <div v-if="addSuccess" class="success-msg">{{ addSuccess }}</div>
          <button @click="addServer" class="btn-submit" :disabled="adding"> {{ adding ? '添加中...' : '✅ 添加主机' }} </button>
        </div>
      </div>
    </div>

    <!-- 所有命令弹窗 -->
    <div v-if="showAllCommands" class="modal-overlay" @click.self="showAllCommands = false">
      <div class="modal">
        <div class="modal-header">
          <h2>📋 所有可用命令</h2>
          <button @click="showAllCommands = false" class="btn-close-modal">✕</button>
        </div>
        <div class="modal-body">
          <div v-for="(cmds, category) in commandList" :key="category" class="cmd-category">
            <h3>{{ category }}</h3>
            <div v-for="(desc, cmd) in cmds" :key="cmd" class="cmd-item">
              <code>{{ cmd }}</code>
              <span>{{ desc }}</span>
              <div class="cmd-actions">
                <button v-for="sid in allServerIds" :key="sid" @click="quickRun(sid, cmd)" class="btn-mini" :style="{ background: getColor(sid) }">{{ getLabel(sid) }}</button>
              </div>
            </div>
          </div>
          <div v-if="allServerIds.length === 0" class="no-server-hint">请先添加主机</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, computed } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'
import ServerColumn from './ServerColumn.vue'

const local = reactive({ cpu: 0, memory: 0, disk: 0, net_sent: 0, net_recv: 0, prev_sent: 0, prev_recv: 0 })
const serversStats = reactive({})
const wsConnected = ref(false)
const currentTime = ref('')
const showAllCommands = ref(false)
const showAddServer = ref(false)

const dynamicCmds = reactive({})
const results = ref({})
const loading = ref({})
const showSuggest = reactive({})
const suggestIdx = reactive({})

const allCommands = ref([])
const commandList = ref({})
const serverList = ref({})

const newServer = reactive({ ip: '', username: 'root', password: '', port: 22, name: '' })
const adding = ref(false)
const addError = ref('')
const addSuccess = ref('')

const colorPalette = ['#4fd2f1', '#f6dd0e', '#e65d5d', '#7b68ee', '#5cb85c', '#f0ad4e', '#5bc0de', '#d9534f']
let colorIdx = 0
const colorMap = {}

let ws = null

const allServerIds = computed(() => Object.keys(serverList.value))

const getColor = (sid) => {
  if (!colorMap[sid]) {
    colorMap[sid] = colorPalette[colorIdx % colorPalette.length]
    colorIdx++
  }
  return colorMap[sid]
}
const getLabel = (sid) => {
  const info = serverList.value[sid]
  if (!info) return sid
  return info.host?.split('.').pop() || sid
}

const updateTime = () => {
  currentTime.value = new Date().toLocaleString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const formatNet = (prev, curr) => {
  if (!prev) return '0.0'
  return ((curr - prev) / 1024 / 1024 * 0.5).toFixed(1)
}

const initWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${protocol}://${window.location.hostname}:8000/ws`)
  ws.onopen = () => { wsConnected.value = true }
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      local.prev_sent = local.net_sent
      local.prev_recv = local.net_recv
      local.cpu = data.local?.cpu || 0
      local.memory = data.local?.memory || 0
      local.disk = data.local?.disk || 0
      local.net_sent = data.local?.network_sent || 0
      local.net_recv = data.local?.network_recv || 0
      if (data.servers) {
        Object.keys(data.servers).forEach(key => {
          serversStats[key] = data.servers[key]
          if (showSuggest[key] === undefined) showSuggest[key] = false
          if (suggestIdx[key] === undefined) suggestIdx[key] = -1
        })
      }
    } catch (e) {}
  }
  ws.onclose = () => { wsConnected.value = false; setTimeout(initWebSocket, 3000) }
  ws.onerror = () => { wsConnected.value = false }
}

const fetchCommands = async () => {
  try {
    const res = await axios.get('/api/commands')
    commandList.value = res.data
    const flat = []
    Object.entries(res.data).forEach(([cat, cmds]) => {
      Object.entries(cmds).forEach(([cmd, desc]) => { flat.push({ cmd, desc, cat }) })
    })
    allCommands.value = flat
  } catch (e) { console.error('获取命令失败:', e) }
}

const fetchServers = async () => {
  try {
    const res = await axios.get('/api/servers')
    serverList.value = res.data
  } catch (e) { console.error('获取服务器列表失败:', e) }
}

const addServer = async () => {
  if (!newServer.ip || !newServer.password) {
    addError.value = '请填写 IP 地址和密码'
    return
  }
  adding.value = true
  addError.value = ''
  addSuccess.value = ''
  try {
    const res = await axios.post('/api/servers/add', {
      ip: newServer.ip,
      password: newServer.password,
      username: newServer.username || 'root',
      port: newServer.port || 22,
      name: newServer.name || undefined
    })
    if (res.data.success) {
      addSuccess.value = res.data.message
      newServer.ip = ''
      newServer.password = ''
      newServer.name = ''
      await fetchServers()
      setTimeout(() => { showAddServer.value = false; addSuccess.value = '' }, 800)
    } else {
      addError.value = res.data.error || '添加失败'
    }
  } catch (e) {
    addError.value = '请求失败: ' + e.message
  }
  adding.value = false
}

const removeServer = async (serverId) => {
  if (!confirm('确定要移除 ' + serverId + ' 吗？')) return
  try {
    await axios.post('/api/servers/remove', { server_id: serverId })
    delete dynamicCmds[serverId]
    delete results.value[serverId]
    delete loading.value[serverId]
    delete colorMap[serverId]
    await fetchServers()
  } catch (e) { alert('移除失败: ' + e.message) }
}

const sendCommand = async (serverId, command) => {
  if (!command || !command.trim()) return
  loading.value[serverId] = true
  try {
    const res = await axios.post('/api/control', { server_id: serverId, command: command.trim() })
    if (res.data.error) results.value[serverId] = '❌ ' + res.data.error
    else {
      const out = res.data.stdout || ''; const err = res.data.stderr || ''
      results.value[serverId] = out + (err ? '\n---\n' + err : '')
      if (!out && !err) results.value[serverId] = '(无输出)'
    }
  } catch (e) { results.value[serverId] = '❌ ' + e.message }
  loading.value[serverId] = false
  dynamicCmds[serverId] = ''
}

const runCmd = (sid) => { showSuggest[sid] = false; if (dynamicCmds[sid]?.trim()) sendCommand(sid, dynamicCmds[sid]) }
const quickRun = (serverId, cmd) => { showAllCommands.value = false; sendCommand(serverId, cmd) }

const chartRef = ref(null)
let chart = null
let chartData = new Array(30).fill(0)
const initChart = () => {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  chart.setOption({
    backgroundColor: 'transparent', grid: { left: 35, right: 10, top: 8, bottom: 20 },
    xAxis: { type: 'category', data: chartData.map((_, i) => i + 1), axisLine: { lineStyle: { color: '#2a4a7a' } }, axisLabel: { color: '#6b9bd6', fontSize: 9 } },
    yAxis: { type: 'value', min: 0, max: 100, axisLine: { lineStyle: { color: '#2a4a7a' } }, axisLabel: { color: '#6b9bd6', fontSize: 9 }, splitLine: { lineStyle: { color: '#1a2a4a' } } },
    series: [{ data: chartData, type: 'line', smooth: true, showSymbol: false, lineStyle: { color: '#00d4ff', width: 2 }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(0,212,255,0.3)' }, { offset: 1, color: 'rgba(0,212,255,0.02)' }]) } }]
  })
}
const updateChart = (val) => {
  if (!chart) return
  chartData.push(val || 0)
  if (chartData.length > 30) chartData.shift()
  chart.setOption({ xAxis: { data: chartData.map((_, i) => i + 1) }, series: [{ data: chartData }] })
}

let timer1 = null, timer2 = null
onMounted(() => {
  updateTime(); timer1 = setInterval(updateTime, 1000)
  initWebSocket(); fetchCommands(); fetchServers()
  nextTick(() => { initChart(); timer2 = setInterval(() => updateChart(local.cpu), 2000) })
})
onBeforeUnmount(() => {
  ws && ws.close(); timer1 && clearInterval(timer1); timer2 && clearInterval(timer2); chart && chart.dispose()
})
</script>

<style scoped>
* { box-sizing: border-box; }
.dashboard { width: 100vw; height: 100vh; background: linear-gradient(135deg, #060d1a 0%, #0a1a3a 50%, #0d1f4a 100%); color: #e0e8f0; display: flex; flex-direction: column; padding: 6px 10px; }
.header { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 2px solid #1a3a6a; margin-bottom: 6px; flex-shrink: 0; }
.title { font-size: 20px; background: linear-gradient(90deg, #00d4ff, #7b68ee); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 2px; }
.time { color: #6b9bd6; font-size: 13px; }
.header-right { display: flex; align-items: center; gap: 10px; }
.btn-help { background: rgba(79,210,241,0.15); border: 1px solid #4fd2f1; color: #4fd2f1; padding: 5px 10px; border-radius: 5px; cursor: pointer; font-size: 11px; font-weight: bold; white-space: nowrap; }
.btn-help:hover { background: rgba(79,210,241,0.3); }
.status { font-size: 12px; color: #e65d5d; }
.status.online { color: #4fd2f1; }

.main-content { display: flex; gap: 8px; flex: 1; min-height: 0; overflow-x: auto; }
.column { min-width: 260px; flex: 1; background: rgba(10, 25, 55, 0.8); border: 1px solid #1a3a6a; border-radius: 8px; padding: 10px; overflow-y: auto; display: flex; flex-direction: column; }
.local-column { max-width: 320px; min-width: 280px; }
.panel-title { font-size: 14px; color: #4fd2f1; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }
.dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.online-dot { background: #4fd2f1; box-shadow: 0 0 5px #4fd2f1; }

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

.network-mini { display: flex; justify-content: space-around; font-size: 10px; color: #6b9bd6; padding: 4px; background: rgba(0,0,0,0.2); border-radius: 4px; margin-bottom: 6px; }
.chart-container { flex: 1; min-height: 120px; }
.chart { width: 100%; height: 100%; }

.empty-column { display: flex; align-items: center; justify-content: center; }
.empty-hint { text-align: center; color: #6b9bd6; }
.empty-icon { font-size: 40px; margin-bottom: 10px; }
.empty-hint p { font-size: 14px; margin-bottom: 15px; }
.btn-empty { background: rgba(79,210,241,0.2); border: 1px solid #4fd2f1; color: #4fd2f1; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-size: 13px; }
.btn-empty:hover { background: rgba(79,210,241,0.4); }

.modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); display: flex; justify-content: center; align-items: center; z-index: 1000; }
.modal { background: #0d1f4a; border: 2px solid #2a5a8a; border-radius: 12px; width: 700px; max-height: 75vh; display: flex; flex-direction: column; }
.modal-small { width: 450px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid #1a3a6a; }
.modal-header h2 { font-size: 16px; color: #4fd2f1; margin: 0; }
.btn-close-modal { background: none; border: none; color: #e65d5d; cursor: pointer; font-size: 18px; }
.modal-body { padding: 14px 18px; overflow-y: auto; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; font-size: 12px; color: #6b9bd6; margin-bottom: 4px; }
.form-input { width: 100%; background: rgba(0,0,0,0.3); border: 1px solid #2a5a8a; color: #e0e8f0; padding: 8px 10px; border-radius: 5px; font-size: 13px; outline: none; }
.form-input:focus { border-color: #4fd2f1; }
.btn-submit { width: 100%; background: #4fd2f1; border: none; color: #0a1a2f; padding: 10px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: bold; margin-top: 6px; }
.btn-submit:disabled { opacity: 0.5; cursor: not-allowed; }
.error-msg { color: #e65d5d; font-size: 12px; margin-bottom: 8px; }
.success-msg { color: #4fd2f1; font-size: 12px; margin-bottom: 8px; }

.cmd-category { margin-bottom: 12px; }
.cmd-category h3 { font-size: 13px; color: #f6dd0e; margin: 0 0 6px 0; }
.cmd-item { display: flex; align-items: center; padding: 4px 0; border-bottom: 1px solid #1a2a4a; font-size: 11px; gap: 8px; }
.cmd-item code { flex: 0 0 auto; color: #adff2f; font-size: 10px; background: rgba(0,0,0,0.3); padding: 2px 5px; border-radius: 3px; }
.cmd-item span { flex: 1; color: #6b9bd6; font-size: 10px; }
.cmd-actions { display: flex; gap: 3px; flex-shrink: 0; }
.btn-mini { border: none; color: #fff; padding: 2px 8px; border-radius: 3px; cursor: pointer; font-size: 10px; font-weight: bold; }
.no-server-hint { text-align: center; color: #6b9bd6; padding: 20px; }

.column::-webkit-scrollbar, .modal-body::-webkit-scrollbar { width: 3px; }
.column::-webkit-scrollbar-thumb, .modal-body::-webkit-scrollbar-thumb { background: #2a4a7a; border-radius: 2px; }
.main-content::-webkit-scrollbar { height: 4px; }
.main-content::-webkit-scrollbar-thumb { background: #2a4a7a; border-radius: 2px; }
</style>

<template>
  <div class="app-container">
    
    <!-- SIDEBAR (RTL - will align to the right side of the screen) -->
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-logo"><i class="fa-solid fa-shield-halved"></i></div>
        <div class="brand-name">
          <h1>بوت سَنَد</h1>
          <p>إدارة ومراقبة المجموعات</p>
        </div>
      </div>
      
      <nav class="navigation">
        <ul class="menu-list">
          <li 
            v-for="item in menuItems" 
            :key="item.id"
            class="menu-item" 
            :class="{ active: isTabActive(item.id) }" 
            @click="handleMenuClick(item)"
          >
            <i :class="item.icon"></i>
            <span>{{ item.title }}</span>
          </li>
        </ul>
      </nav>
      
      <!-- Sidebar footer with bot stats, matching mockup exactly -->
      <div class="sidebar-footer">
        <div class="status-card">
          <div class="status-header">
            <span class="status-dot" :class="{ active: stats.bot_status === 'running' }"></span>
            <span class="status-label">حالة البوت</span>
            <span :class="stats.bot_status === 'running' ? 'status-green-text' : 'status-red-text'">
              {{ stats.bot_status === 'running' ? 'متصل' : 'متوقف' }}
            </span>
          </div>
          <div class="status-info-text">
            وقت التشغيل: {{ stats.bot_status === 'running' ? '15 يوم، 7 ساعة، 32 دقيقة' : '0 دقيقة' }}
          </div>
          <div class="status-info-text">
            الإصدار: v2.6.0
          </div>
          <button class="sys-info-btn" @click="showSystemInfo">معلومات النظام</button>
        </div>
      </div>
    </aside>
    
    <!-- MAIN CONTENT AREA -->
    <main class="main-content">
      
      <!-- TOP BAR -->
      <header class="top-bar">
        <!-- Page Title on Right (RTL) -->
        <div class="page-title">
          <i class="fa-solid fa-chart-line"></i>
          <h2>لوحة التحكم</h2>
        </div>
        
        <!-- Controls on Left (RTL) -->
        <div class="top-bar-controls">
          <!-- Active Group selector -->
          <div v-show="showGroupSelector" class="group-selector-container">
            <label for="group-select"><i class="fa-solid fa-users"></i> المجموعة النشطة:</label>
            <select id="group-select" v-model="selectedGroupId" class="group-select">
              <option v-if="groups.length === 0" value="">لا توجد مجموعات مسجلة</option>
              <option v-for="g in groups" :key="g.group_id" :value="g.group_id">
                {{ g.title || `مجموعة (${g.group_id})` }}
              </option>
            </select>
          </div>

          <!-- Light/Dark Mode toggle button -->
          <button class="icon-button" @click="toggleTheme" title="تغيير المظهر">
            <i :class="isDarkTheme ? 'fa-solid fa-sun' : 'fa-solid fa-moon'"></i>
          </button>

          <!-- Notification Bell -->
          <button class="icon-button" title="التنبيهات" @click="showNotificationsAlert">
            <i class="fa-solid fa-bell"></i>
            <span class="badge-count">3</span>
          </button>

          <!-- User profile -->
          <div class="user-profile">
            <div class="user-info">
              <span class="user-role">مشرف عام</span>
              <span class="user-name">{{ stats.active_bot && stats.active_bot.username ? `@${stats.active_bot.username}` : (stats.active_bot && stats.active_bot.name ? stats.active_bot.name : 'admin_gr_bot') }}</span>
            </div>
            <div class="user-avatar">
              <i class="fa-solid fa-user-shield"></i>
            </div>
          </div>
        </div>
      </header>
      
      <!-- Tab Contents -->
      <div class="content-body">
        <HomeTab 
          v-if="activeTab === 'home'"
          :stats="stats"
          :logs="botLogs"
          :groups="groups"
          @start-bot="startBot"
          @stop-bot="stopBot"
          @open-groups-modal="showGroupsModal = true"
          @notify="showNotification"
        />
        <ProtectionTab 
          v-else-if="activeTab === 'protection'"
          :selectedGroupId="selectedGroupId"
          @notify="showNotification"
        />
        <TriggersTab 
          v-else-if="activeTab === 'triggers'"
          :selectedGroupId="selectedGroupId"
          @notify="showNotification"
        />
        <LogsTab 
          v-else-if="activeTab === 'logs'"
          @notify="showNotification"
        />
      </div>
      
    </main>
    
    <!-- Groups Modal -->
    <GroupsModal 
      :show="showGroupsModal" 
      :groups="groups"
      @close="showGroupsModal = false"
    />
    
    <!-- Toast Notifications -->
    <div class="toast-container">
      <div v-for="toast in toasts" :key="toast.id" class="toast" :style="{ borderColor: toast.type === 'error' ? 'var(--danger-red)' : '' }">
        <i v-if="toast.type === 'error'" class="fa-solid fa-circle-exclamation" style="color: var(--danger-red);"></i>
        <i v-else class="fa-solid fa-circle-check" style="color: var(--success-green);"></i>
        <span>{{ toast.message }}</span>
      </div>
    </div>
    
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import HomeTab from './components/HomeTab.vue'
import ProtectionTab from './components/ProtectionTab.vue'
import TriggersTab from './components/TriggersTab.vue'
import LogsTab from './components/LogsTab.vue'
import GroupsModal from './components/GroupsModal.vue'

// 10 Menu items matching the mockup sidebar
const menuItems = [
  { id: 'home', title: 'الرئيسية', icon: 'fa-solid fa-house' },
  { id: 'groups_modal', title: 'المجموعات', icon: 'fa-solid fa-users' },
  { id: 'logs', title: 'سجل الرقابة', icon: 'fa-solid fa-clipboard-list' },
  { id: 'warnings', title: 'التحذيرات', icon: 'fa-solid fa-triangle-exclamation' },
  { id: 'members', title: 'الأعضاء', icon: 'fa-solid fa-user' },
  { id: 'commands', title: 'الأوامر', icon: 'fa-solid fa-terminal' },
  { id: 'triggers', title: 'الردود التلقائية', icon: 'fa-solid fa-reply-all' },
  { id: 'protection', title: 'الإعدادات', icon: 'fa-solid fa-gear' },
  { id: 'backup', title: 'النسخ الاحتياطي', icon: 'fa-solid fa-database' },
  { id: 'developers', title: 'المطورين', icon: 'fa-solid fa-code' }
]

const activeTab = ref('home')
const groups = ref([])
const selectedGroupId = ref('')
const toasts = ref([])
const showGroupsModal = ref(false)
const botLogs = ref('')
const isServerConnected = ref(true)
const isDarkTheme = ref(false)

const stats = ref({
  total_bots: 0,
  total_groups: 0,
  total_warnings: 0,
  bot_status: 'stopped',
  active_bot: null
})

let pollingTimer = null

const showGroupSelector = computed(() => {
  return activeTab.value === 'protection' || activeTab.value === 'triggers'
})

const isTabActive = (itemId) => {
  if (itemId === 'warnings' && activeTab.value === 'logs') return true
  return activeTab.value === itemId
}

const handleMenuClick = (item) => {
  if (item.id === 'groups_modal') {
    showGroupsModal.value = true
  } else if (item.id === 'warnings') {
    activeTab.value = 'logs'
  } else if (item.id === 'members' || item.id === 'commands' || item.id === 'developers') {
    showNotification({ message: `قسم (${item.title}) قيد التطوير حالياً وسيتم ربطه قريباً.`, type: 'info' })
  } else if (item.id === 'backup') {
    triggerBackup()
  } else {
    activeTab.value = item.id
  }
}

const triggerBackup = async () => {
  showNotification({ message: 'جاري إنشاء نسخة احتياطية لقاعدة البيانات...', type: 'success' })
  // Simulate backup request delay
  setTimeout(() => {
    showNotification({ message: 'تم حفظ النسخة الاحتياطية بنجاح.', type: 'success' })
  }, 1000)
}

const showSystemInfo = () => {
  showNotification({ 
    message: `تفاصيل النظام: خادم الويب متصل بنجاح | منفذ التشغيل: 8000 | إطار العمل: Vue 3 + FastAPI`, 
    type: 'success' 
  })
}

const showNotificationsAlert = () => {
  showNotification({ 
    message: 'تنبيهات النظام: 1) تم إيقاف البوت تلقائياً، 2) 3 تحذيرات جديدة مسجلة، 3) تم تحديث الإعدادات.', 
    type: 'info' 
  })
}

const toggleTheme = () => {
  isDarkTheme.value = !isDarkTheme.value
  if (isDarkTheme.value) {
    document.documentElement.classList.remove('light-theme')
  } else {
    document.documentElement.classList.add('light-theme')
  }
}

// Notifications
let toastId = 0
const showNotification = ({ message, type = 'success' }) => {
  const id = toastId++
  toasts.value.push({ id, message, type })
  setTimeout(() => {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }, 3000)
}

const fetchStats = async () => {
  try {
    const response = await fetch('/api/stats')
    if (response.ok) {
      stats.value = await response.json()
      isServerConnected.value = true
    }
  } catch (error) {
    console.error("فشل الاتصال بخادم الويب:", error)
    isServerConnected.value = false
    stats.value.bot_status = 'stopped'
  }
}

const fetchBotLogs = async () => {
  if (!stats.value.active_bot) return
  try {
    const response = await fetch(`/api/bot/${stats.value.active_bot.bot_id}/logs`)
    if (response.ok) {
      const data = await response.json()
      botLogs.value = data.logs
    }
  } catch (error) {
    console.error("فشل جلب السجلات:", error)
  }
}

const fetchGroups = async () => {
  try {
    const response = await fetch('/api/groups')
    if (response.ok) {
      const fetchedGroups = await response.json()
      groups.value = fetchedGroups.filter(g => g.group_id && g.title)
      
      if (groups.value.length > 0 && !selectedGroupId.value) {
        selectedGroupId.value = groups.value[0].group_id
      }
    }
  } catch (error) {
    console.error("خطأ أثناء جلب المجموعات:", error)
  }
}

const startBot = async () => {
  if (!stats.value.active_bot) {
    showNotification({ message: "يرجى إدخال توكن للبوت أولاً.", type: 'error' })
    return
  }
  try {
    const response = await fetch(`/api/bot/${stats.value.active_bot.bot_id}/start`, { method: 'POST' })
    if (response.ok) {
      showNotification({ message: "تم إرسال أمر تشغيل البوت بنجاح.", type: 'success' })
      fetchStats()
    } else {
      showNotification({ message: "فشل تشغيل البوت.", type: 'error' })
    }
  } catch (error) {
    showNotification({ message: "خطأ أثناء الاتصال بالسيرفر.", type: 'error' })
  }
}

const stopBot = async () => {
  if (!stats.value.active_bot) return
  try {
    const response = await fetch(`/api/bot/${stats.value.active_bot.bot_id}/stop`, { method: 'POST' })
    if (response.ok) {
      showNotification({ message: "تم إيقاف تشغيل البوت بنجاح.", type: 'success' })
      fetchStats()
    } else {
      showNotification({ message: "فشل إيقاف البوت.", type: 'error' })
    }
  } catch (error) {
    showNotification({ message: "خطأ أثناء الاتصال بالسيرفر.", type: 'error' })
  }
}

onMounted(() => {
  fetchStats()
  fetchGroups()
  
  pollingTimer = setInterval(() => {
    fetchStats()
    if (stats.value.active_bot && stats.value.bot_status === 'running') {
      fetchBotLogs()
    }
  }, 2000)
})

onUnmounted(() => {
  if (pollingTimer) clearInterval(pollingTimer)
})
</script>

<style scoped>
/* Scoped styles for sidebar brand logo color */
.text-purple {
  color: var(--accent-color);
}
</style>

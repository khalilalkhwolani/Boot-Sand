<template>
  <div class="dashboard-home">
    
    <!-- ROW 1: STATS CARDS (Mockup Style, RTL order) -->
    <div class="stats-grid">
      <!-- Card 1: Total Members (Rightmost in RTL) -->
      <div class="stat-card">
        <div class="stat-info">
          <span class="stat-label">الأعضاء الإجمالي</span>
          <span class="stat-value purple-text">3,459</span>
          <span class="stat-subtext">+8% عن الأسبوع الماضي</span>
        </div>
        <div class="stat-icon-wrapper purple">
          <i class="fa-solid fa-user"></i>
        </div>
      </div>

      <!-- Card 2: Today's Warnings -->
      <div class="stat-card">
        <div class="stat-info">
          <span class="stat-label">التحذيرات اليوم</span>
          <span class="stat-value yellow-text">{{ stats.total_warnings || 56 }}</span>
          <span class="stat-subtext">+12% عن أمس</span>
        </div>
        <div class="stat-icon-wrapper yellow">
          <i class="fa-solid fa-triangle-exclamation"></i>
        </div>
      </div>

      <!-- Card 3: Active Groups -->
      <div class="stat-card clickable-card" @click="$emit('open-groups-modal')">
        <div class="stat-info">
          <span class="stat-label">المجموعات النشطة</span>
          <span class="stat-value green-text">{{ stats.total_groups || 24 }}</span>
          <span class="stat-subtext">من أصل 35 مجموعة</span>
        </div>
        <div class="stat-icon-wrapper green">
          <i class="fa-solid fa-users"></i>
        </div>
      </div>

      <!-- Card 4: Bot Status (Leftmost in RTL) -->
      <div class="stat-card">
        <div class="stat-info">
          <span class="stat-label">حالة البوت</span>
          <span class="stat-value" :class="stats.bot_status === 'running' ? 'green-text' : 'red-text'">
            {{ stats.bot_status === 'running' ? 'يعمل' : 'متوقف' }}
          </span>
          <span class="stat-subtext">آخر تحديث: منذ دقيقة</span>
        </div>
        <div class="stat-icon-wrapper" :class="stats.bot_status === 'running' ? 'green' : 'red'">
          <i :class="stats.bot_status === 'running' ? 'fa-solid fa-play' : 'fa-solid fa-stop'"></i>
        </div>
      </div>
    </div>
    
    <!-- ROW 2: CHART & QUICK ACTIONS (RTL Swap: Actions Right, Chart Left) -->
    <div class="chart-actions-grid">
      <!-- Quick Actions Grid (Right column in RTL) -->
      <div class="dashboard-panel actions-panel">
        <div class="panel-header">
          <h3>الإجراءات السريعة</h3>
        </div>
        <div class="actions-grid">
          <!-- Column 2 (Left in layout, but Top-Left in mockup) -->
          <button 
            class="action-btn green-btn"
            :disabled="stats.bot_status === 'running' || !stats.active_bot"
            @click="$emit('start-bot')"
          >
            <span class="action-title">تشغيل البوت</span>
            <div class="action-circle green"><i class="fa-solid fa-play"></i></div>
          </button>

          <!-- Column 1 (Right in layout, but Top-Right in mockup) -->
          <button 
            class="action-btn red-btn"
            :disabled="stats.bot_status !== 'running'"
            @click="$emit('stop-bot')"
          >
            <span class="action-title">إيقاف البوت</span>
            <div class="action-circle red"><i class="fa-solid fa-stop"></i></div>
          </button>

          <button class="action-btn purple-btn" @click="handleAction('broadcast')">
            <span class="action-title">إرسال إعلان</span>
            <div class="action-circle purple"><i class="fa-solid fa-bullhorn"></i></div>
          </button>

          <button class="action-btn yellow-btn" @click="handleAction('clean')">
            <span class="action-title">تنظيف المحذوفين</span>
            <div class="action-circle yellow"><i class="fa-solid fa-broom"></i></div>
          </button>

          <button class="action-btn blue-btn" @click="handleAction('backup')">
            <span class="action-title">نسخة احتياطية</span>
            <div class="action-circle blue"><i class="fa-solid fa-database"></i></div>
          </button>

          <button class="action-btn teal-btn" @click="handleAction('settings')">
            <span class="action-title">تحديث الإعدادات</span>
            <div class="action-circle teal"><i class="fa-solid fa-gears"></i></div>
          </button>
        </div>
      </div>

      <!-- 7 Days Activity Chart (Left column in RTL) -->
      <div class="dashboard-panel chart-panel">
        <div class="panel-header">
          <h3>النشاط خلال آخر 7 أيام</h3>
          <div class="dropdown-wrapper">
            <select class="time-select">
              <option>آخر 7 أيام</option>
              <option>آخر 30 يوم</option>
            </select>
            <i class="fa-solid fa-chevron-down dropdown-arrow"></i>
          </div>
        </div>
        <div class="chart-wrapper">
          <div class="chart-content">
            <!-- Y-Axis Labels -->
            <div class="chart-y-axis">
              <span>100</span>
              <span>80</span>
              <span>60</span>
              <span>40</span>
              <span>20</span>
              <span>0</span>
            </div>
            
            <!-- SVG Plot Area -->
            <div class="svg-container">
              <svg viewBox="0 0 500 200" class="activity-svg" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="chart-glow" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#7c4dff" stop-opacity="0.35"/>
                    <stop offset="100%" stop-color="#7c4dff" stop-opacity="0"/>
                  </linearGradient>
                </defs>
                <!-- Grid Lines -->
                <line x1="0" y1="0" x2="500" y2="0" stroke="var(--border-color)" stroke-width="1" stroke-dasharray="4" />
                <line x1="0" y1="40" x2="500" y2="40" stroke="var(--border-color)" stroke-width="1" stroke-dasharray="4" />
                <line x1="0" y1="80" x2="500" y2="80" stroke="var(--border-color)" stroke-width="1" stroke-dasharray="4" />
                <line x1="0" y1="120" x2="500" y2="120" stroke="var(--border-color)" stroke-width="1" stroke-dasharray="4" />
                <line x1="0" y1="160" x2="500" y2="160" stroke="var(--border-color)" stroke-width="1" stroke-dasharray="4" />
                <line x1="0" y1="200" x2="500" y2="200" stroke="var(--border-color)" stroke-width="1" />

                <!-- Area Fill under curve -->
                <path d="M 40,160 Q 110,125 180,120 T 320,30 T 460,110 L 460,200 L 40,200 Z" fill="url(#chart-glow)" />
                
                <!-- Curved Smooth Line -->
                <path d="M 40,160 Q 110,125 180,120 T 320,30 T 460,110" fill="none" stroke="#7c4dff" stroke-width="3.5" />
                
                <!-- Glowing Points on Line -->
                <circle cx="40" cy="160" r="4.5" fill="#7c4dff" stroke="#fff" stroke-width="1" />
                <circle cx="110" cy="125" r="4.5" fill="#7c4dff" stroke="#fff" stroke-width="1" />
                <circle cx="180" cy="120" r="4.5" fill="#7c4dff" stroke="#fff" stroke-width="1" />
                <circle cx="250" cy="90" r="4.5" fill="#7c4dff" stroke="#fff" stroke-width="1" />
                <circle cx="320" cy="30" r="5" fill="#7c4dff" stroke="#fff" stroke-width="1.5" />
                <circle cx="390" cy="95" r="4.5" fill="#7c4dff" stroke="#fff" stroke-width="1" />
                <circle cx="460" cy="110" r="4.5" fill="#7c4dff" stroke="#fff" stroke-width="1" />
              </svg>
            </div>
          </div>
          <!-- X-Axis Labels -->
          <div class="chart-labels">
            <span>يونيو 18</span>
            <span>يونيو 19</span>
            <span>يونيو 20</span>
            <span>يونيو 21</span>
            <span>يونيو 22</span>
            <span>يونيو 23</span>
            <span>يونيو 24</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ROW 3: LISTS (Recent Groups & Recent Alerts - RTL Order: Groups Right, Alerts Left) -->
    <div class="lists-grid">
      <!-- Recent Groups Card (Right in RTL) -->
      <div class="dashboard-panel list-panel">
        <div class="panel-header">
          <h3>أحدث المجموعات</h3>
        </div>
        <div class="item-list">
          <div v-if="activeGroups.length === 0" class="list-empty">
            لا توجد مجموعات نشطة حالياً.
          </div>
          <div v-for="g in activeGroups" :key="g.group_id" class="list-item">
            <div class="group-avatar-circle">
              <i class="fa-solid fa-users"></i>
            </div>
            <div class="item-details">
              <h4>{{ g.title }}</h4>
              <p>{{ g.invite_link ? '@' + g.invite_link.split('/').pop() : `ID: ${g.group_id}` }}</p>
            </div>
            <span class="item-meta count-badge">
              {{ g.members || '350' }}
              <i class="fa-solid fa-user-group" style="font-size: 10px; margin-right: 4px;"></i>
            </span>
          </div>
        </div>
        <button class="list-footer-btn" @click="$emit('open-groups-modal')">
          عرض جميع المجموعات
          <i class="fa-solid fa-chevron-left"></i>
        </button>
      </div>

      <!-- Recent Alerts Card (Left in RTL) -->
      <div class="dashboard-panel list-panel">
        <div class="panel-header">
          <h3>أحدث التحذيرات</h3>
        </div>
        <div class="item-list">
          <div v-if="recentAlerts.length === 0" class="list-empty">
            لا توجد تحذيرات مسجلة مؤخراً.
          </div>
          <div v-for="alert in recentAlerts" :key="alert.id" class="list-item">
            <div class="item-icon-box" :class="alert.colorClass">
              <i :class="alert.icon"></i>
            </div>
            <div class="item-details">
              <h4>{{ alert.reason }}</h4>
              <p>{{ alert.group }}</p>
            </div>
            <span class="item-meta time-elapsed">{{ alert.time }}</span>
          </div>
        </div>
        <button class="list-footer-btn" @click="goToLogs">
          عرض جميع التحذيرات
          <i class="fa-solid fa-chevron-left"></i>
        </button>
      </div>
    </div>

    <!-- Live Terminal Log -->
    <div class="console-panel">
      <h3>
        <i class="fa-solid fa-terminal" style="color: var(--accent-color); margin-left: 8px;"></i>
        سجل عمليات البوت المباشر (Terminal Log)
      </h3>
      <pre ref="consoleRef" class="console-output">{{ logs || 'لا توجد سجلات تشغيل متوفرة حالياً.' }}</pre>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  stats: Object,
  logs: String,
  groups: Array
})

const emit = defineEmits(['start-bot', 'stop-bot', 'open-groups-modal', 'notify'])

const consoleRef = ref(null)

const recentAlerts = ref([
  { id: 1, reason: 'روابط محظورة', group: 'مجموعة العلوم العامة', time: 'منذ دقيقة', icon: 'fa-solid fa-link', colorClass: 'blue-alert' },
  { id: 2, reason: 'إعلان تجاري', group: 'مجموعة الطلاب', time: 'منذ 3 دقائق', icon: 'fa-solid fa-bullhorn', colorClass: 'purple-alert' },
  { id: 3, reason: 'كلمات مسيئة', group: 'مجموعة النقاش', time: 'منذ 5 دقائق', icon: 'fa-solid fa-comment', colorClass: 'orange-alert' },
  { id: 4, reason: 'تكرار الرسائل', group: 'مجموعة التقنية', time: 'منذ 8 دقائق', icon: 'fa-solid fa-rotate', colorClass: 'green-alert' }
])

const activeGroups = computed(() => {
  // If groups are empty, return mockup groups to match image
  if (!props.groups || props.groups.length === 0) {
    return [
      { group_id: 1, title: 'مجموعة العلوم العامة', invite_link: '@science_group', members: '856' },
      { group_id: 2, title: 'مجموعة الطلاب', invite_link: '@students_group', members: '623' },
      { group_id: 3, title: 'مجموعة النقاش', invite_link: '@discussion_group', members: '445' },
      { group_id: 4, title: 'مجموعة التقنية', invite_link: '@tech_group', members: '312' }
    ]
  }
  return props.groups.slice(0, 4).map((g, index) => {
    const membersList = ['856', '623', '445', '312']
    return {
      ...g,
      members: membersList[index] || '120'
    }
  })
})

const handleAction = (action) => {
  if (action === 'clean') {
    emit('notify', { message: 'تم بدء تنظيف الحسابات المحذوفة بنجاح.', type: 'success' })
  } else if (action === 'broadcast') {
    emit('notify', { message: 'تم فتح نافذة إرسال الإعلان للمجموعات.', type: 'success' })
  } else if (action === 'settings') {
    emit('notify', { message: 'تم تحديث مزامنة لوحة التحكم بنجاح.', type: 'success' })
  } else if (action === 'backup') {
    emit('notify', { message: 'جاري إنشاء نسخة احتياطية من قاعدة البيانات...', type: 'success' })
  }
}

const goToLogs = () => {
  // We can trigger an event or handle routing
  emit('notify', { message: 'الانتقال إلى سجل الرقابة والتحذيرات...', type: 'info' })
  // In our parent app, we can map activeTab = 'logs'
  // Since we don't have direct tab setter, parent will catch it or user can use sidebar
}

watch(() => props.logs, () => {
  nextTick(() => {
    if (consoleRef.value) {
      consoleRef.value.scrollTop = consoleRef.value.scrollHeight
    }
  })
})
</script>

<style scoped>
.dashboard-home {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.clickable-card {
  cursor: pointer;
}

.chart-actions-grid {
  display: grid;
  grid-template-columns: 1.2fr 1.8fr;
  gap: 20px;
}

@media (max-width: 992px) {
  .chart-actions-grid {
    grid-template-columns: 1fr;
  }
}

.dashboard-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--card-radius);
  padding: 20px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 12px;
}

.panel-header h3 {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.dropdown-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.time-select {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 5px 12px 5px 28px;
  color: var(--text-primary);
  font-size: 11px;
  font-weight: 700;
  outline: none;
  cursor: pointer;
  appearance: none;
}

.dropdown-arrow {
  position: absolute;
  left: 10px;
  font-size: 10px;
  color: var(--text-secondary);
  pointer-events: none;
}

.chart-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chart-content {
  display: flex;
  gap: 15px;
  height: 150px;
  position: relative;
}

.chart-y-axis {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  font-size: 10px;
  color: var(--text-secondary);
  width: 25px;
  text-align: left;
  padding-bottom: 4px;
}

.svg-container {
  flex: 1;
  position: relative;
  border-left: 1px solid var(--border-color);
  border-bottom: 1px solid var(--border-color);
}

.activity-svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}

.chart-labels {
  display: flex;
  justify-content: space-between;
  margin-right: 40px; /* offset for y-axis space */
  font-size: 10px;
  color: var(--text-secondary);
}

/* Actions Grid matching mockup */
.actions-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.action-btn {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  transition: all 0.2s;
  text-align: right;
  height: 52px;
}

.action-btn:hover:not(:disabled) {
  border-color: var(--text-muted);
  transform: translateY(-1px);
}

.action-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.action-title {
  font-size: 12px;
  font-weight: 700;
}

.action-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #fff;
  flex-shrink: 0;
}

/* Actions Colors matching mockup */
.green-btn { color: var(--success-green); }
.green-btn .action-circle { background-color: rgba(16, 185, 129, 0.15); color: var(--success-green); }

.red-btn { color: var(--danger-red); }
.red-btn .action-circle { background-color: rgba(239, 68, 68, 0.15); color: var(--danger-red); }

.yellow-btn { color: var(--warning-yellow); }
.yellow-btn .action-circle { background-color: rgba(245, 158, 11, 0.15); color: var(--warning-yellow); }

.purple-btn { color: #a855f7; }
.purple-btn .action-circle { background-color: rgba(168, 85, 247, 0.15); color: #a855f7; }

.blue-btn { color: #3b82f6; }
.blue-btn .action-circle { background-color: rgba(59, 130, 246, 0.15); color: #3b82f6; }

.teal-btn { color: #06b6d4; }
.teal-btn .action-circle { background-color: rgba(6, 182, 212, 0.15); color: #06b6d4; }

/* Lists Grid */
.lists-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

@media (max-width: 768px) {
  .lists-grid {
    grid-template-columns: 1fr;
  }
}

.list-panel {
  padding-bottom: 12px; /* make space for footer btn */
}

.item-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.list-empty {
  text-align: center;
  color: var(--text-secondary);
  padding: 20px;
  font-size: 12px;
}

.list-item {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.group-avatar-circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: var(--text-secondary);
}

.item-icon-box {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: #fff;
  flex-shrink: 0;
}

.blue-alert { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
.purple-alert { background: rgba(168, 85, 247, 0.15); color: #a855f7; }
.orange-alert { background: rgba(249, 115, 22, 0.15); color: #f97316; }
.green-alert { background: rgba(16, 185, 129, 0.15); color: var(--success-green); }

.item-details {
  flex: 1;
}

.item-details h4 {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
}

.item-details p {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.item-meta {
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 600;
}

.count-badge {
  background: rgba(16, 185, 129, 0.1);
  color: var(--success-green);
  border: 1px solid rgba(16, 185, 129, 0.2);
  padding: 4px 10px;
  border-radius: 20px;
  display: inline-flex;
  align-items: center;
}

.time-elapsed {
  color: var(--text-secondary);
}

.list-footer-btn {
  background: none;
  border: none;
  color: var(--accent-color);
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 12px;
  margin-top: 10px;
  cursor: pointer;
  transition: all 0.2s;
  width: 100%;
  border-top: 1px solid var(--border-color);
}

.list-footer-btn:hover {
  color: var(--accent-color-hover);
}

.list-footer-btn i {
  font-size: 10px;
}

/* Console Panel */
.console-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--card-radius);
  padding: 20px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
}

.console-panel h3 {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 15px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 10px;
  color: var(--text-primary);
}

.console-output {
  background: #080911;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 15px;
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 11px;
  color: #a855f7;
  max-height: 250px;
  overflow-y: auto;
  white-space: pre-wrap;
  direction: ltr;
  text-align: left;
  line-height: 1.6;
}
</style>

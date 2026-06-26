<template>
  <div class="settings-grid">
    
    <!-- Warning List -->
    <div class="table-card">
      <h3><i class="fa-solid fa-triangle-exclamation" style="color: var(--danger-red); margin-left: 8px;"></i> قائمة الأعضاء المحذرين بالمجموعة</h3>
      <div class="table-container scrollable-table">
        <table class="responsive-table">
          <thead>
            <tr>
              <th>معرف العضو (User ID)</th>
              <th>معرف المجموعة</th>
              <th style="text-align: center;">التحذيرات (Warnings)</th>
              <th style="width: 100px; text-align: center;">التحكم</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="warnings.length === 0">
              <td colspan="4" class="table-empty">
                لا يوجد أعضاء حاصلين على تحذيرات حالياً في قاعدة البيانات.
              </td>
            </tr>
            <tr v-for="w in warnings" :key="w.user_id + '-' + w.group_id">
              <td>{{ w.user_id }}</td>
              <td style="color: var(--text-secondary); font-size: 12px;">{{ w.group_id }}</td>
              <td style="text-align: center;">
                <span class="badge badge-warning">{{ w.warn_count }} / 10</span>
              </td>
              <td style="text-align: center;">
                <button class="btn-danger-small" @click="resetUserWarning(w.group_id, w.user_id)">
                  <i class="fa-solid fa-rotate-left"></i> تصفير
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    
    <!-- Message Logs -->
    <div class="table-card">
      <h3><i class="fa-solid fa-comment-medical" style="color: var(--accent-color); margin-left: 8px;"></i> آخر الرسائل المستلمة والخاضعة للرقابة</h3>
      <div class="table-container scrollable-table">
        <table class="responsive-table">
          <thead>
            <tr>
              <th>اسم العضو</th>
              <th>محتوى الرسالة</th>
              <th>الوقت</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="logs.length === 0">
              <td colspan="3" class="table-empty">
                لا توجد رسائل مسجلة حالياً.
              </td>
            </tr>
            <tr v-for="l in logs" :key="l.timestamp + '-' + l.user_id">
              <td class="username-cell">{{ l.username ? '@' + l.username : l.full_name }}</td>
              <td>{{ l.message_text }}</td>
              <td class="time-cell">{{ formatTime(l.timestamp) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const emit = defineEmits(['notify'])

const warnings = ref([])
const logs = ref([])
let pollInterval = null

const fetchMessageLogs = async () => {
  try {
    const response = await fetch('/api/logs/messages?limit=50')
    if (response.ok) {
      logs.value = await response.json()
    }
  } catch (error) {
    console.error("فشل جلب سجل الرسائل:", error)
  }
}

const fetchWarnings = async () => {
  try {
    const response = await fetch('/api/warnings')
    if (response.ok) {
      warnings.value = await response.json()
    }
  } catch (error) {
    console.error("فشل جلب قائمة التحذيرات:", error)
  }
}

const resetUserWarning = async (groupId, userId) => {
  if (!confirm(`هل أنت متأكد من رغبتك في تصفير تحذيرات هذا العضو؟`)) return
  try {
    const res = await fetch('/api/warning/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ group_id: groupId, user_id: userId })
    })
    if (res.ok) {
      emit('notify', { message: "تم تصفير تحذيرات العضو بنجاح.", type: 'success' })
      fetchWarnings()
    } else {
      emit('notify', { message: "فشل تصفير التحذيرات.", type: 'error' })
    }
  } catch (error) {
    emit('notify', { message: "حدث خطأ في الشبكة.", type: 'error' })
  }
}

const formatTime = (ts) => {
  return new Date(ts * 1000).toLocaleTimeString('ar-SA')
}

onMounted(() => {
  fetchMessageLogs()
  fetchWarnings()
  
  // Refresh logs and warnings every 3 seconds while this tab is active
  pollInterval = setInterval(() => {
    fetchMessageLogs()
    fetchWarnings()
  }, 3000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<style scoped>
.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 20px;
}

.table-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--card-radius);
  padding: 25px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
}

.table-card h3 {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 12px;
  color: var(--text-primary);
}

.scrollable-table {
  max-height: 400px;
  overflow-y: auto;
}

.table-container {
  overflow-x: auto;
  border-radius: 10px;
  border: 1px solid var(--border-color);
}

.responsive-table {
  width: 100%;
  border-collapse: collapse;
  text-align: right;
}

.responsive-table th {
  background: var(--bg-primary);
  padding: 12px 18px;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-color);
}

.responsive-table td {
  padding: 12px 18px;
  font-size: 13px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-primary);
  vertical-align: middle;
}

.table-empty {
  text-align: center;
  color: var(--text-secondary);
  padding: 30px !important;
}

.username-cell {
  font-weight: 600;
  color: var(--accent-color);
}

.time-cell {
  color: var(--text-secondary);
  font-size: 12px;
}

.badge {
  display: inline-block;
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 700;
  border-radius: 6px;
}

.badge-warning {
  background: rgba(255, 145, 0, 0.15);
  color: #ff9100;
  border: 1px solid rgba(255, 145, 0, 0.25);
}

.btn-danger-small {
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.25);
  color: var(--danger-red);
  padding: 5px 10px;
  font-size: 11px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
  border: none;
}

.btn-danger-small:hover {
  background: var(--danger-red);
  color: #fff;
}
</style>

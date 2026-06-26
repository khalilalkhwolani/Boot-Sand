<template>
  <div v-if="!selectedGroupId" class="no-group-selected">
    <i class="fa-solid fa-message"></i>
    <p>يرجى اختيار مجموعة نشطة من القائمة العلوية لإدارة الردود التلقائية.</p>
  </div>
  
  <div v-else class="table-card">
    <h3><i class="fa-solid fa-comment-dots" style="color: var(--accent-color); margin-left: 8px;"></i> إضافة رد تلقائي ذكي</h3>
    
    <div class="trigger-form-inline">
      <div class="form-group flex-1">
        <label for="new-trigger-key">الكلمة المفتاحية (Keyword):</label>
        <input 
          type="text" 
          id="new-trigger-key" 
          v-model="newTrigger.keyword" 
          class="form-control" 
          placeholder="مثال: موقع الكلية"
        >
      </div>
      <div class="form-group flex-2">
        <label for="new-trigger-val">الرد المخصص للبوت (Response Reply):</label>
        <input 
          type="text" 
          id="new-trigger-val" 
          v-model="newTrigger.response" 
          class="form-control" 
          placeholder="تفضل رابط موقع الكلية الرسمي هو: ..."
        >
      </div>
      <button class="btn btn-primary" @click="addCustomTrigger">
        <i class="fa-solid fa-plus"></i> إضافة الرد
      </button>
    </div>
    
    <h3 style="margin-top: 30px;"><i class="fa-solid fa-table-list" style="color: var(--accent-color); margin-left: 8px;"></i> الكلمات والردود المسجلة حالياً</h3>
    <div class="table-container">
      <table class="responsive-table">
        <thead>
          <tr>
            <th>الكلمة المفتاحية (Keyword)</th>
            <th>الرد التلقائي (Response Reply)</th>
            <th style="width: 100px; text-align: center;">إجراءات</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="triggers.length === 0">
            <td colspan="3" class="table-empty">
              لا توجد ردود تلقائية مسجلة لهذه المجموعة حالياً.
            </td>
          </tr>
          <tr v-for="t in triggers" :key="t.keyword">
            <td class="keyword-cell">{{ t.keyword }}</td>
            <td>{{ t.response }}</td>
            <td style="text-align: center;">
              <button class="btn-icon btn-icon-danger" @click="deleteCustomTrigger(t.keyword)">
                <i class="fa-solid fa-trash"></i>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'

const props = defineProps({
  selectedGroupId: [String, Number]
})

const emit = defineEmits(['notify'])

const triggers = ref([])
const newTrigger = ref({
  keyword: '',
  response: ''
})

const fetchGroupTriggers = async () => {
  if (!props.selectedGroupId) return
  try {
    const response = await fetch(`/api/group/${props.selectedGroupId}/triggers`)
    if (response.ok) {
      triggers.value = await response.json()
    }
  } catch (error) {
    console.error("خطأ أثناء جلب الردود التلقائية:", error)
  }
}

const addCustomTrigger = async () => {
  if (!props.selectedGroupId) return
  
  const keyword = newTrigger.value.keyword.trim()
  const response = newTrigger.value.response.trim()
  
  if (!keyword || !response) {
    emit('notify', { message: 'يرجى ملء الكلمة والرد للتمكن من الإضافة.', type: 'error' })
    return
  }
  
  try {
    const res = await fetch(`/api/group/${props.selectedGroupId}/trigger`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keyword, response })
    })
    
    if (res.ok) {
      emit('notify', { message: 'تمت إضافة الرد التلقائي بنجاح.', type: 'success' })
      newTrigger.value.keyword = ''
      newTrigger.value.response = ''
      fetchGroupTriggers()
    } else {
      emit('notify', { message: 'فشل إضافة الرد.', type: 'error' })
    }
  } catch (error) {
    emit('notify', { message: 'حدث خطأ في الشبكة.', type: 'error' })
  }
}

const deleteCustomTrigger = async (keyword) => {
  if (!props.selectedGroupId || !confirm(`هل أنت متأكد من رغبتك في حذف الرد التلقائي للكلمة "${keyword}"؟`)) return
  
  try {
    const res = await fetch(`/api/group/${props.selectedGroupId}/trigger/${encodeURIComponent(keyword)}`, {
      method: 'DELETE'
    })
    
    if (res.ok) {
      emit('notify', { message: 'تم حذف الرد التلقائي.', type: 'success' })
      fetchGroupTriggers()
    } else {
      emit('notify', { message: 'فشل الحذف.', type: 'error' })
    }
  } catch (error) {
    emit('notify', { message: 'حدث خطأ في الشبكة.', type: 'error' })
  }
}

watch(() => props.selectedGroupId, () => {
  fetchGroupTriggers()
})

onMounted(() => {
  fetchGroupTriggers()
})
</script>

<style scoped>
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

.trigger-form-inline {
  display: flex;
  align-items: flex-end;
  gap: 15px;
  flex-wrap: wrap;
  background: var(--bg-primary);
  padding: 15px;
  border-radius: 10px;
  border: 1px solid var(--border-color);
}

.form-group {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  font-size: 12px;
  margin-bottom: 8px;
  color: var(--text-secondary);
  font-weight: 600;
}

.form-control {
  width: 100%;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 10px 14px;
  color: var(--text-primary);
  font-size: 13px;
  transition: all 0.3s;
}

.form-control:focus {
  border-color: var(--accent-color);
  outline: none;
}

.flex-1 { flex: 1; min-width: 200px; }
.flex-2 { flex: 2; min-width: 300px; }

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
}

.table-empty {
  text-align: center;
  color: var(--text-secondary);
  padding: 30px !important;
}

.keyword-cell {
  font-weight: 700;
  color: var(--accent-color);
}

.btn-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s;
  background: none;
}

.btn-icon-danger {
  color: var(--danger-red);
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.15);
}
.btn-icon-danger:hover {
  background: var(--danger-red);
  color: #fff;
}
</style>

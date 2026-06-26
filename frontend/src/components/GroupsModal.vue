<template>
  <div v-if="show" class="modal-overlay" @click="closeModal">
    <div class="modal-card" @click.stop>
      <div class="modal-header">
        <h3>
          <i class="fa-solid fa-users" style="color: var(--accent-cyan); margin-left: 8px;"></i>
          المجموعات المراقبة النشطة
        </h3>
        <button class="modal-close-btn" @click="$emit('close')">&times;</button>
      </div>
      <div class="modal-body">
        <div v-if="activeGroups.length === 0" class="empty-state">
          <i class="fa-solid fa-users-slash"></i>
          <p>لا توجد مجموعات نشطة ومراقبة حالياً.</p>
        </div>
        <div v-else>
          <div v-for="g in activeGroups" :key="g.group_id" class="modal-group-item">
            <div class="modal-group-info">
              <h4>{{ g.title || `مجموعة (${g.group_id})` }}</h4>
              <p><i class="fa-solid fa-hashtag" style="font-size: 10px;"></i> ID: {{ g.group_id }}</p>
            </div>
            <a 
              v-if="g.invite_link" 
              :href="g.invite_link" 
              target="_blank" 
              class="modal-group-link-btn"
            >
              <i class="fa-brands fa-telegram"></i> انتقال للمجموعة
            </a>
            <span 
              v-else 
              class="modal-group-link-btn disabled" 
              title="البوت غير مشرف في المجموعة لتوليد رابط دعوة"
            >
              <i class="fa-solid fa-link-slash"></i> لا يوجد رابط
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  show: Boolean,
  groups: Array
})

const emit = defineEmits(['close'])

const activeGroups = computed(() => {
  return props.groups.filter(g => g.group_id && g.title)
})

const closeModal = () => {
  emit('close')
}
</script>

<style scoped>
.empty-state {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}
.empty-state i {
  font-size: 40px;
  margin-bottom: 15px;
  color: var(--accent-purple);
}
</style>

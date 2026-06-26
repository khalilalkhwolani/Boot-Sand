<template>
  <div v-if="!selectedGroupId" class="no-group-selected">
    <i class="fa-solid fa-users-viewfinder"></i>
    <p>يرجى اختيار مجموعة نشطة من القائمة العلوية للتحكم بإعدادات الحماية.</p>
  </div>
  
  <div v-else class="settings-grid">
    
    <!-- SECTION 1: CORE SECURITY MODULES -->
    <div class="settings-card card-full">
      <h3><i class="fa-solid fa-shield-halved" style="color: var(--accent-color); margin-left: 8px;"></i> وحدات الحماية والرقابة النشطة</h3>
      <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 25px;">قم بتفعيل أو تعطيل وحدات الحماية المطبقة على هذه المجموعة فورا:</p>
      
      <div class="switch-grid">
        <div class="switch-row">
          <div class="switch-info">
            <h4>منع الروابط والـ Links</h4>
            <p>حذف رسائل الأعضاء التي تحتوي على روابط مواقع وتنبيههم تلقائياً.</p>
          </div>
          <label class="switch">
            <input 
              type="checkbox" 
              v-model="settings.anti_link" 
              @change="toggleSetting('anti_link')"
            >
            <span class="slider"></span>
          </label>
        </div>

        <div class="switch-row">
          <div class="switch-info">
            <h4>منع الاعلانات والسبام (Spam)</h4>
            <p>كشف الرسائل الترويجية وأرقام الهواتف الشائعة في الإعلانات وحذفها.</p>
          </div>
          <label class="switch">
            <input 
              type="checkbox" 
              v-model="settings.anti_spam" 
              @change="toggleSetting('anti_spam')"
            >
            <span class="slider"></span>
          </label>
        </div>

        <div class="switch-row">
          <div class="switch-info">
            <h4>معالجة الذكاء الاصطناعي (Gemini AI)</h4>
            <p>استدعاء نموذج الذكاء الاصطناعي للتحقق من الرسائل المشبوهة وحذفها والتعلم منها.</p>
          </div>
          <label class="switch">
            <input 
              type="checkbox" 
              v-model="settings.gemini_enabled" 
              @change="toggleSetting('gemini_enabled')"
            >
            <span class="slider"></span>
          </label>
        </div>

        <div class="switch-row">
          <div class="switch-info">
            <h4>كابتشا البوتات (Captcha)</h4>
            <p>تقييد الأعضاء الجدد ومنعهم من الكتابة حتى يقوموا بحل التحقق بنجاح.</p>
          </div>
          <label class="switch">
            <input 
              type="checkbox" 
              v-model="settings.captcha_enabled" 
              @change="toggleSetting('captcha_enabled')"
            >
            <span class="slider"></span>
          </label>
        </div>

        <div class="switch-row">
          <div class="switch-info">
            <h4>منع الإغراق (Anti-Flood)</h4>
            <p>كتم العضو تلقائياً لمدة 10 دقائق إذا أرسل أكثر من 5 رسائل في 3 ثوانٍ.</p>
          </div>
          <label class="switch">
            <input 
              type="checkbox" 
              v-model="settings.anti_flood" 
              @change="toggleSetting('anti_flood')"
            >
            <span class="slider"></span>
          </label>
        </div>

        <div class="switch-row">
          <div class="switch-info">
            <h4>منع الشتائم والألفاظ (Censorship)</h4>
            <p>حذف الرسائل التي تحتوي على ألفاظ وشتائم غير لائقة محددة مسبقاً.</p>
          </div>
          <label class="switch">
            <input 
              type="checkbox" 
              v-model="settings.censorship_enabled" 
              @change="toggleSetting('censorship_enabled')"
            >
            <span class="slider"></span>
          </label>
        </div>

        <div class="switch-row">
          <div class="switch-info">
            <h4>قفل المجموعة المجدول</h4>
            <p>منع إرسال الرسائل للأعضاء تلقائياً في ساعات الليل أو ساعات محددة.</p>
          </div>
          <label class="switch">
            <input 
              type="checkbox" 
              v-model="settings.lock_enabled" 
              @change="toggleSetting('lock_enabled')"
            >
            <span class="slider"></span>
          </label>
        </div>
      </div>
    </div>

    <!-- SECTION 2: MEDIA FILTER GRID -->
    <div class="settings-card card-full">
      <h3><i class="fa-solid fa-photo-film" style="color: var(--accent-color); margin-left: 8px;"></i> فلترة الوسائط والمرفقات (Media Filter)</h3>
      <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 25px;">قم بقفل أنواع معينة من المرفقات والوسائط لمنع الإزعاج في المجموعة:</p>
      
      <div class="switch-grid">
        <div class="switch-row">
          <div class="switch-info">
            <h4>منع الملصقات (Anti-Sticker)</h4>
            <p>حذف الملصقات (Stickers) المرسلة من الأعضاء.</p>
          </div>
          <label class="switch">
            <input 
              type="checkbox" 
              v-model="settings.anti_sticker" 
              @change="toggleSetting('anti_sticker')"
            >
            <span class="slider"></span>
          </label>
        </div>

        <div class="switch-row">
          <div class="switch-info">
            <h4>منع الصور المتحركة (Anti-GIF)</h4>
            <p>حذف الصور المتحركة (GIFs) المزعجة.</p>
          </div>
          <label class="switch">
            <input 
              type="checkbox" 
              v-model="settings.anti_gif" 
              @change="toggleSetting('anti_gif')"
            >
            <span class="slider"></span>
          </label>
        </div>

        <div class="switch-row">
          <div class="switch-info">
            <h4>منع الصور (Anti-Photo)</h4>
            <p>منع الأعضاء من إرسال الصور العادية في المجموعة.</p>
          </div>
          <label class="switch">
            <input 
              type="checkbox" 
              v-model="settings.anti_photo" 
              @change="toggleSetting('anti_photo')"
            >
            <span class="slider"></span>
          </label>
        </div>

        <div class="switch-row">
          <div class="switch-info">
            <h4>منع الفيديوهات (Anti-Video)</h4>
            <p>منع الأعضاء من إرسال مقاطع الفيديو في المجموعة.</p>
          </div>
          <label class="switch">
            <input 
              type="checkbox" 
              v-model="settings.anti_video" 
              @change="toggleSetting('anti_video')"
            >
            <span class="slider"></span>
          </label>
        </div>

        <div class="switch-row">
          <div class="switch-info">
            <h4>منع الملفات والكتب (Anti-Document)</h4>
            <p>منع رفع الملفات المضغوطة أو الكتب (ZIP/PDF) لحماية المجموعة.</p>
          </div>
          <label class="switch">
            <input 
              type="checkbox" 
              v-model="settings.anti_document" 
              @change="toggleSetting('anti_document')"
            >
            <span class="slider"></span>
          </label>
        </div>
      </div>
    </div>
    
    <!-- SECTION 3: TEXT & CONFIGURATIONS -->
    
    <!-- Welcome message settings card -->
    <div class="settings-card">
      <h3><i class="fa-solid fa-hands-clapping" style="color: var(--accent-color); margin-left: 8px;"></i> الترحيب بالأعضاء الجدد</h3>
      
      <div class="switch-row" style="margin-bottom: 20px;">
        <div class="switch-info">
          <h4>تفعيل رسالة الترحيب</h4>
          <p>إرسال ترحيب منسق في المجموعة عند انضمام عضو حقيقي بنجاح.</p>
        </div>
        <label class="switch">
          <input 
            type="checkbox" 
            v-model="settings.welcome_enabled" 
            @change="toggleSetting('welcome_enabled')"
          >
          <span class="slider"></span>
        </label>
      </div>
      
      <div class="form-group">
        <label for="setting-welcome-msg">نص رسالة الترحيب المخصصة:</label>
        <textarea 
          id="setting-welcome-msg" 
          v-model="settings.welcome_message" 
          class="form-control" 
          rows="4" 
          placeholder="اكتب ترحيباً مميزاً بالأعضاء الجدد..."
        ></textarea>
        <p class="field-hint">استخدم <code class="hint-code">{name}</code> لوضع اسم العضو الجديد تلقائياً في الترحيب.</p>
      </div>
      
      <button class="btn btn-primary" @click="saveWelcomeMessage">
        <i class="fa-solid fa-floppy-disk"></i> حفظ رسالة الترحيب
      </button>
    </div>

    <!-- Banned Words Config Card -->
    <div class="settings-card">
      <h3><i class="fa-solid fa-ban" style="color: var(--accent-color); margin-left: 8px;"></i> الكلمات المحظورة والشتائم</h3>
      <p style="font-size: 11px; color: var(--text-secondary); margin-bottom: 15px;">
        اكتب الكلمات أو الشتائم التي ترغب في حذفها تلقائياً من القروب، مفصولة بفاصلة (، أو ,):
      </p>
      
      <div class="form-group">
        <label for="banned-words-input">قائمة الكلمات والشتائم المحظورة:</label>
        <textarea 
          id="banned-words-input" 
          v-model="settings.banned_words" 
          class="form-control" 
          rows="5" 
          placeholder="مثال: غبي, كلب, حيوان, يا حمار"
        ></textarea>
      </div>
      
      <button class="btn btn-primary" @click="saveBannedWords">
        <i class="fa-solid fa-floppy-disk"></i> حفظ قائمة الكلمات
      </button>
    </div>

    <!-- Scheduled Lock Config Card -->
    <div class="settings-card">
      <h3><i class="fa-solid fa-clock-rotate-left" style="color: var(--accent-color); margin-left: 8px;"></i> توقيت قفل المجموعة المجدول</h3>
      <p style="font-size: 11px; color: var(--text-secondary); margin-bottom: 15px;">
        حدد الساعات التي يُمنع فيها الكتابة للأعضاء نهائياً (تطبيقاً لخيار قفل المجموعة المجدول أعلاه):
      </p>
      
      <div class="lock-times-row">
        <div class="form-group flex-1">
          <label for="lock-start-time">ساعة بدء القفل:</label>
          <input 
            type="time" 
            id="lock-start-time" 
            v-model="settings.lock_start" 
            class="form-control"
          />
        </div>
        <div class="form-group flex-1">
          <label for="lock-end-time">ساعة فتح المجموعة:</label>
          <input 
            type="time" 
            id="lock-end-time" 
            v-model="settings.lock_end" 
            class="form-control"
          />
        </div>
      </div>
      
      <button class="btn btn-primary" style="margin-top: 20px;" @click="saveLockTimes">
        <i class="fa-solid fa-floppy-disk"></i> حفظ مواقيت القفل
      </button>
    </div>
    
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'

const props = defineProps({
  selectedGroupId: [String, Number]
})

const emit = defineEmits(['notify'])

const settings = ref({
  anti_link: false,
  anti_spam: false,
  gemini_enabled: false,
  captcha_enabled: false,
  welcome_enabled: false,
  welcome_message: '',
  
  // New features configuration
  anti_flood: false,
  censorship_enabled: false,
  banned_words: '',
  lock_enabled: false,
  lock_start: '23:00',
  lock_end: '06:00',
  
  anti_sticker: false,
  anti_gif: false,
  anti_photo: false,
  anti_video: false,
  anti_document: false
})

const fetchGroupSettings = async () => {
  if (!props.selectedGroupId) return
  try {
    const response = await fetch(`/api/group/${props.selectedGroupId}/settings`)
    if (response.ok) {
      const data = await response.json()
      settings.value = {
        anti_link: data.anti_link === 1,
        anti_spam: data.anti_spam === 1,
        gemini_enabled: data.gemini_enabled === 1,
        captcha_enabled: data.captcha_enabled === 1,
        welcome_enabled: data.welcome_enabled === 1,
        welcome_message: data.welcome_message || '',
        
        anti_flood: data.anti_flood === 1,
        censorship_enabled: data.censorship_enabled === 1,
        banned_words: data.banned_words || '',
        lock_enabled: data.lock_enabled === 1,
        lock_start: data.lock_start || '23:00',
        lock_end: data.lock_end || '06:00',
        
        anti_sticker: data.anti_sticker === 1,
        anti_gif: data.anti_gif === 1,
        anti_photo: data.anti_photo === 1,
        anti_video: data.anti_video === 1,
        anti_document: data.anti_document === 1
      }
    }
  } catch (error) {
    console.error("خطأ أثناء جلب إعدادات المجموعة:", error)
  }
}

const toggleSetting = async (settingName) => {
  if (!props.selectedGroupId) return
  
  const originalValue = settings.value[settingName]
  const val = originalValue ? 1 : 0
  const payload = {}
  payload[settingName] = val
  
  try {
    const response = await fetch(`/api/group/${props.selectedGroupId}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    
    if (response.ok) {
      emit('notify', { message: 'تم تحديث خيار الحماية بنجاح.', type: 'success' })
    } else {
      emit('notify', { message: 'فشل تحديث الخيار.', type: 'error' })
      settings.value[settingName] = !originalValue
    }
  } catch (error) {
    emit('notify', { message: 'حدث خطأ في الشبكة.', type: 'error' })
    settings.value[settingName] = !originalValue
  }
}

const saveWelcomeMessage = async () => {
  if (!props.selectedGroupId) return
  try {
    const response = await fetch(`/api/group/${props.selectedGroupId}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ welcome_message: settings.value.welcome_message })
    })
    if (response.ok) {
      emit('notify', { message: 'تم حفظ رسالة الترحيب بنجاح.', type: 'success' })
    } else {
      emit('notify', { message: 'فشل حفظ رسالة الترحيب.', type: 'error' })
    }
  } catch (error) {
    emit('notify', { message: 'حدث خطأ في الشبكة.', type: 'error' })
  }
}

const saveBannedWords = async () => {
  if (!props.selectedGroupId) return
  try {
    const response = await fetch(`/api/group/${props.selectedGroupId}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ banned_words: settings.value.banned_words })
    })
    if (response.ok) {
      emit('notify', { message: 'تم حفظ الكلمات المحظورة بنجاح.', type: 'success' })
    } else {
      emit('notify', { message: 'فشل حفظ الكلمات المحظورة.', type: 'error' })
    }
  } catch (error) {
    emit('notify', { message: 'حدث خطأ في الشبكة.', type: 'error' })
  }
}

const saveLockTimes = async () => {
  if (!props.selectedGroupId) return
  try {
    const response = await fetch(`/api/group/${props.selectedGroupId}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        lock_start: settings.value.lock_start,
        lock_end: settings.value.lock_end
      })
    })
    if (response.ok) {
      emit('notify', { message: 'تم حفظ أوقات القفل المجدولة بنجاح.', type: 'success' })
    } else {
      emit('notify', { message: 'فشل حفظ أوقات القفل.', type: 'error' })
    }
  } catch (error) {
    emit('notify', { message: 'حدث خطأ في الشبكة.', type: 'error' })
  }
}

// Watch group id change
watch(() => props.selectedGroupId, () => {
  fetchGroupSettings()
})

onMounted(() => {
  fetchGroupSettings()
})
</script>

<style scoped>
.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 20px;
}

.card-full {
  grid-column: 1 / -1;
}

.settings-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--card-radius);
  padding: 25px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
}

.settings-card h3 {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 12px;
  color: var(--text-primary);
}

.switch-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
}

.switch-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  background: var(--bg-primary);
  padding: 15px;
  border-radius: 10px;
  border: 1px solid var(--border-color);
}

.switch-info h4 {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.switch-info p {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.5;
}

/* Switch UI */
.switch {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 26px;
  flex-shrink: 0;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--border-color);
  transition: .4s;
  border-radius: 34px;
  border: 1px solid var(--border-color);
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: var(--text-secondary);
  transition: .4s;
  border-radius: 50%;
}

.light-theme .slider {
  background-color: #cbd5e1;
  border-color: #cbd5e1;
}

input:checked + .slider {
  background: var(--accent-color);
  border-color: var(--accent-color);
}

input:checked + .slider:before {
  transform: translateX(24px);
  background-color: #fff;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 13px;
  margin-bottom: 8px;
  color: var(--text-secondary);
}

.form-control {
  width: 100%;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 12px 15px;
  color: var(--text-primary);
  font-size: 13px;
  resize: vertical;
  transition: all 0.3s;
}

.form-control:focus {
  border-color: var(--accent-color);
  outline: none;
}

.field-hint {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 6px;
}

.hint-code {
  color: var(--accent-color);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
}

.lock-times-row {
  display: flex;
  gap: 15px;
  align-items: center;
}

.flex-1 {
  flex: 1;
}
</style>

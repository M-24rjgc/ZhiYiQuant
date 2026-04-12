<template>
  <div class="profile-page" :class="{ 'theme-dark': isDarkTheme }">
    <div class="page-header">
      <h2 class="page-title">
        <a-icon type="user" />
        <span>本地账户</span>
      </h2>
      <p class="page-desc">管理当前桌面账户资料、安全信息和通知偏好。</p>
    </div>

    <a-row :gutter="24">
      <a-col :xs="24" :lg="8">
        <a-card :bordered="false" class="profile-summary">
          <div class="summary-avatar">
            <a-avatar :size="92" :src="profile.avatar || '/avatar2.jpg'" />
          </div>
          <h3>{{ profile.nickname || profile.username || 'Owner' }}</h3>
          <p>{{ profile.email || '本地桌面账户' }}</p>
          <div class="summary-meta">
            <div class="meta-item">
              <span class="meta-label">用户名</span>
              <span class="meta-value">{{ profile.username || 'owner' }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">最近登录</span>
              <span class="meta-value">{{ formatTime(profile.last_login_at) || '-' }}</span>
            </div>
          </div>
        </a-card>
      </a-col>

      <a-col :xs="24" :lg="16">
        <a-card :bordered="false">
          <a-tabs default-active-key="basic">
            <a-tab-pane key="basic" tab="基本资料">
              <a-form :form="profileForm" layout="vertical">
                <a-form-item label="显示名称">
                  <a-input
                    v-decorator="['nickname', { initialValue: profile.nickname }]"
                    placeholder="输入显示名称"
                  />
                </a-form-item>
                <a-form-item label="邮箱">
                  <a-input
                    v-decorator="['email', { initialValue: profile.email }]"
                    placeholder="输入邮箱（可选）"
                  />
                </a-form-item>
                <a-form-item>
                  <a-button type="primary" :loading="savingProfile" @click="handleSaveProfile">
                    保存资料
                  </a-button>
                </a-form-item>
              </a-form>
            </a-tab-pane>

            <a-tab-pane key="password" tab="修改密码">
              <a-form :form="passwordForm" layout="vertical">
                <a-form-item label="当前密码">
                  <a-input-password
                    v-decorator="['old_password', { rules: [{ required: true, message: '请输入当前密码' }] }]"
                    placeholder="输入当前密码"
                  />
                </a-form-item>
                <a-form-item label="新密码">
                  <a-input-password
                    v-decorator="['new_password', { rules: [{ required: true, message: '请输入新密码' }, { min: 8, message: '密码至少 8 位' }] }]"
                    placeholder="输入新密码"
                  />
                </a-form-item>
                <a-form-item label="确认新密码">
                  <a-input-password
                    v-decorator="['confirm_password', { rules: [{ required: true, message: '请确认新密码' }, { validator: validateConfirmPassword }] }]"
                    placeholder="再次输入新密码"
                  />
                </a-form-item>
                <a-form-item>
                  <a-button type="primary" :loading="savingPassword" @click="handleChangePassword">
                    更新密码
                  </a-button>
                </a-form-item>
              </a-form>
            </a-tab-pane>

            <a-tab-pane key="notifications" tab="通知设置">
              <a-alert
                type="info"
                show-icon
                message="为策略运行、组合监控和告警选择默认通知方式。"
                style="margin-bottom: 16px;"
              />
              <a-form :form="notificationForm" layout="vertical">
                <a-form-item label="默认通知渠道">
                  <a-checkbox-group
                    v-decorator="['default_channels', { initialValue: notificationSettings.default_channels || ['browser'] }]"
                  >
                    <a-row :gutter="16">
                      <a-col :span="8"><a-checkbox value="browser">桌面通知</a-checkbox></a-col>
                      <a-col :span="8"><a-checkbox value="telegram">Telegram</a-checkbox></a-col>
                      <a-col :span="8"><a-checkbox value="email">邮件</a-checkbox></a-col>
                    </a-row>
                    <a-row :gutter="16" style="margin-top: 8px;">
                      <a-col :span="8"><a-checkbox value="discord">Discord</a-checkbox></a-col>
                      <a-col :span="8"><a-checkbox value="webhook">Webhook</a-checkbox></a-col>
                      <a-col :span="8"><a-checkbox value="phone">短信</a-checkbox></a-col>
                    </a-row>
                  </a-checkbox-group>
                </a-form-item>

                <a-form-item label="Telegram Bot Token">
                  <a-input-password v-decorator="['telegram_bot_token', { initialValue: notificationSettings.telegram_bot_token }]" />
                </a-form-item>
                <a-form-item label="Telegram Chat ID">
                  <a-input v-decorator="['telegram_chat_id', { initialValue: notificationSettings.telegram_chat_id }]" />
                </a-form-item>
                <a-form-item label="通知邮箱">
                  <a-input v-decorator="['email_notify', { initialValue: notificationSettings.email }]" />
                </a-form-item>
                <a-form-item label="Discord Webhook">
                  <a-input v-decorator="['discord_webhook', { initialValue: notificationSettings.discord_webhook }]" />
                </a-form-item>
                <a-form-item label="Webhook URL">
                  <a-input v-decorator="['webhook_url', { initialValue: notificationSettings.webhook_url }]" />
                </a-form-item>
                <a-form-item label="Webhook Token">
                  <a-input-password v-decorator="['webhook_token', { initialValue: notificationSettings.webhook_token }]" />
                </a-form-item>
                <a-form-item label="短信号码">
                  <a-input v-decorator="['phone', { initialValue: notificationSettings.phone }]" />
                </a-form-item>
                <a-form-item>
                  <a-button type="primary" :loading="savingNotifications" @click="handleSaveNotifications">
                    保存通知设置
                  </a-button>
                  <a-button style="margin-left: 12px;" :loading="testingNotification" @click="handleTestNotification">
                    发送测试通知
                  </a-button>
                </a-form-item>
              </a-form>
            </a-tab-pane>
          </a-tabs>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script>
import { baseMixin } from '@/store/app-mixin'
import {
  getProfile,
  updateProfile,
  changePassword,
  getNotificationSettings,
  updateNotificationSettings,
  testNotification
} from '@/api/user'

export default {
  name: 'Profile',
  mixins: [baseMixin],
  beforeCreate () {
    this.profileForm = this.$form.createForm(this, { name: 'profileForm' })
    this.passwordForm = this.$form.createForm(this, { name: 'passwordForm' })
    this.notificationForm = this.$form.createForm(this, { name: 'notificationForm' })
  },
  data () {
    return {
      profile: {},
      notificationSettings: {
        default_channels: ['browser']
      },
      savingProfile: false,
      savingPassword: false,
      savingNotifications: false,
      testingNotification: false
    }
  },
  computed: {
    isDarkTheme () {
      return this.navTheme === 'dark' || this.navTheme === 'realdark'
    }
  },
  mounted () {
    this.loadProfile()
    this.loadNotifications()
  },
  methods: {
    validateConfirmPassword (rule, value, callback) {
      const password = this.passwordForm.getFieldValue('new_password')
      if (value && value !== password) {
        callback(new Error('两次输入的密码不一致'))
      } else {
        callback()
      }
    },
    async loadProfile () {
      const res = await getProfile()
      if (res.code === 1 && res.data) {
        this.profile = res.data
        this.profileForm.setFieldsValue({
          nickname: res.data.nickname || '',
          email: res.data.email || ''
        })
      }
    },
    async loadNotifications () {
      const res = await getNotificationSettings()
      if (res.code === 1 && res.data) {
        this.notificationSettings = {
          default_channels: ['browser'],
          ...res.data
        }
        this.notificationForm.setFieldsValue({
          default_channels: this.notificationSettings.default_channels || ['browser'],
          telegram_bot_token: this.notificationSettings.telegram_bot_token || '',
          telegram_chat_id: this.notificationSettings.telegram_chat_id || '',
          email_notify: this.notificationSettings.email || '',
          discord_webhook: this.notificationSettings.discord_webhook || '',
          webhook_url: this.notificationSettings.webhook_url || '',
          webhook_token: this.notificationSettings.webhook_token || '',
          phone: this.notificationSettings.phone || ''
        })
      }
    },
    handleSaveProfile () {
      this.profileForm.validateFields(async (err, values) => {
        if (err) return
        this.savingProfile = true
        try {
          const res = await updateProfile(values)
          if (res.code === 1) {
            this.$message.success('资料已保存')
            await this.loadProfile()
          } else {
            this.$message.error(res.msg || '保存失败')
          }
        } finally {
          this.savingProfile = false
        }
      })
    },
    handleChangePassword () {
      this.passwordForm.validateFields(async (err, values) => {
        if (err) return
        this.savingPassword = true
        try {
          const res = await changePassword({
            old_password: values.old_password,
            new_password: values.new_password,
            confirm_password: values.confirm_password
          })
          if (res.code === 1) {
            this.$message.success('密码已更新')
            this.passwordForm.resetFields()
          } else {
            this.$message.error(res.msg || '密码更新失败')
          }
        } finally {
          this.savingPassword = false
        }
      })
    },
    handleSaveNotifications () {
      this.notificationForm.validateFields(async (err, values) => {
        if (err) return
        this.savingNotifications = true
        try {
          const res = await updateNotificationSettings({
            default_channels: values.default_channels,
            telegram_bot_token: values.telegram_bot_token,
            telegram_chat_id: values.telegram_chat_id,
            email: values.email_notify,
            discord_webhook: values.discord_webhook,
            webhook_url: values.webhook_url,
            webhook_token: values.webhook_token,
            phone: values.phone
          })
          if (res.code === 1) {
            this.$message.success('通知设置已保存')
            await this.loadNotifications()
          } else {
            this.$message.error(res.msg || '通知设置保存失败')
          }
        } finally {
          this.savingNotifications = false
        }
      })
    },
    async handleTestNotification () {
      this.testingNotification = true
      try {
        const res = await testNotification()
        if (res.code === 1) {
          this.$message.success('测试通知已发送，请检查目标渠道收件箱')
        } else {
          this.$message.error(res.msg || '测试通知发送失败')
        }
      } catch (error) {
        const data = error && error.response && error.response.data ? error.response.data : {}
        const failed = (data && data.data && data.data.failed) ? data.data.failed : {}
        const details = Object.keys(failed).map(ch => {
          const err = (failed[ch] && failed[ch].error) ? failed[ch].error : 'unknown_error'
          return `${ch}: ${err}`
        })
        const msg = details.length ? `测试通知失败 - ${details.join(' | ')}` : (data.msg || '测试通知发送失败')
        this.$message.error(msg)
      } finally {
        this.testingNotification = false
      }
    },
    formatTime (value) {
      if (!value) return ''
      return new Date(value).toLocaleString('zh-CN')
    }
  }
}
</script>

<style lang="less" scoped>
.page-header {
  margin-bottom: 24px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.page-desc {
  margin: 0;
  color: #6b7e87;
}

.profile-summary {
  text-align: center;
}

.summary-avatar {
  margin-bottom: 16px;
}

.summary-meta {
  margin-top: 24px;
  text-align: left;
}

.meta-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-top: 1px solid #eef2f4;
}

.meta-label {
  color: #7a8c94;
}

.meta-value {
  color: #17333c;
  font-weight: 500;
}
</style>

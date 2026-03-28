<template>
  <div class="desktop-login">
    <div class="login-shell">
      <div class="brand-panel">
        <div class="brand-pill">桌面量化工作台</div>
        <img src="~@/assets/brand-full.png" alt="智弈量化" class="brand-logo-full">
        <p class="brand-copy">本地优先的量化研究、分析与交易工作台。</p>
        <div class="brand-tags">
          <span>本地数据</span>
          <span>AI 分析</span>
          <span>策略回测</span>
        </div>
      </div>

      <a-card class="login-card" :bordered="false">
        <div class="card-eyebrow">本地运行</div>
        <div class="card-title">本地登录</div>

        <a-alert
          v-if="!runtimeReady"
          type="info"
          showIcon
          message="本地引擎启动中，请稍候。"
          style="margin-bottom: 16px;"
        />

        <a-alert
          v-if="loginError"
          type="error"
          showIcon
          :message="loginError"
          style="margin-bottom: 16px;"
        />

        <a-form :form="loginForm" @submit="handleLogin">
          <a-form-item>
            <a-input
              size="large"
              placeholder="用户名"
              v-decorator="[
                'username',
                { rules: [{ required: true, message: '请输入用户名' }], initialValue: 'owner' }
              ]"
            >
              <a-icon slot="prefix" type="user" />
            </a-input>
          </a-form-item>

          <a-form-item>
            <a-input-password
              size="large"
              placeholder="密码"
              v-decorator="[
                'password',
                { rules: [{ required: true, message: '请输入密码' }] }
              ]"
            >
              <a-icon slot="prefix" type="lock" />
            </a-input-password>
          </a-form-item>

          <a-form-item style="margin-bottom: 8px;">
            <a-button
              size="large"
              type="primary"
              htmlType="submit"
              class="submit-button"
              :disabled="!runtimeReady"
              :loading="loginLoading"
              block
            >
              进入桌面
            </a-button>
          </a-form-item>
        </a-form>

        <div class="login-hint">默认账户为 `owner`，请使用你当前设置的本地密码登录。</div>
      </a-card>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DesktopLogin',
  beforeCreate () {
    this.loginForm = this.$form.createForm(this, { name: 'desktopLogin' })
  },
  data () {
    return {
      loginLoading: false,
      loginError: '',
      runtimeReady: typeof window === 'undefined' ? true : window.__ZHIYIQUANT_RUNTIME_READY__ !== false
    }
  },
  mounted () {
    if (typeof window !== 'undefined') {
      window.addEventListener('zhiyiquant:runtime-ready', this.handleRuntimeReady)
    }
  },
  beforeDestroy () {
    if (typeof window !== 'undefined') {
      window.removeEventListener('zhiyiquant:runtime-ready', this.handleRuntimeReady)
    }
  },
  methods: {
    handleRuntimeReady (event) {
      this.runtimeReady = !!(event && event.detail && event.detail.ready)
      if (this.runtimeReady) {
        this.loginError = ''
      }
    },
    handleLogin (e) {
      e.preventDefault()
      this.loginError = ''

      if (!this.runtimeReady) {
        this.loginError = '本地引擎仍在启动，请稍候再试。'
        return
      }

      this.loginForm.validateFields((err, values) => {
        if (err) return

        this.loginLoading = true
        this.$store.dispatch('Login', values)
          .then(() => {
            const redirect = this.$route.query.redirect || '/'
            this.$router.push({ path: redirect })
          })
          .catch(error => {
            const fallback = error?.message === 'Network Error'
              ? '本地引擎尚未就绪或启动失败，请稍候再试。'
              : '登录失败'
            this.loginError = error?.response?.data?.msg || fallback
          })
          .finally(() => {
            this.loginLoading = false
          })
      })
    }
  }
}
</script>

<style lang="less" scoped>
.desktop-login {
  width: 100%;
  min-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-shell {
  width: 100%;
  max-width: 960px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 388px);
  gap: 20px;
  align-items: center;
}

.brand-panel,
.login-card {
  min-width: 0;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(32, 88, 106, 0.08);
  box-shadow: 0 18px 54px rgba(18, 48, 60, 0.10);
  backdrop-filter: blur(18px);
}

.brand-panel {
  padding: clamp(22px, 2.4vw, 34px);
  display: flex;
  flex-direction: column;
  justify-content: center;
  overflow: hidden;
}

.brand-pill {
  display: inline-flex;
  align-self: flex-start;
  padding: 7px 11px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.8px;
  color: #0b6c84;
  background: rgba(19, 194, 194, 0.12);
}

.brand-copy {
  margin: 16px 0 0;
  max-width: 390px;
  font-size: 15px;
  line-height: 1.65;
  color: #49636f;
}

.brand-logo-full {
  width: 100%;
  max-width: 392px;
  height: auto;
  margin-top: 18px;
}

.brand-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;

  span {
    padding: 8px 12px;
    border-radius: 999px;
    font-size: 12px;
    color: #214651;
    background: rgba(255, 255, 255, 0.74);
    border: 1px solid rgba(24, 76, 91, 0.08);
  }
}

.login-card {
  padding: 28px 24px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.card-eyebrow {
  margin-bottom: 10px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 1.2px;
  color: #0f7b97;
}

.card-title {
  margin-bottom: 16px;
  font-size: 24px;
  font-weight: 700;
  color: #163745;
}

.submit-button {
  height: 46px;
  border: none;
  border-radius: 14px;
  background: linear-gradient(135deg, #1f9ad7 0%, #1d71f2 100%);
  box-shadow: 0 16px 32px rgba(29, 113, 242, 0.24);
}

.login-hint {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.6;
  color: #607781;
}

@media (max-height: 860px) {
  .brand-panel,
  .login-card {
    padding: 22px 20px;
  }

  .brand-logo-full {
    max-width: 316px;
    margin-top: 14px;
  }

  .brand-copy {
    margin-top: 12px;
    font-size: 14px;
  }

  .brand-tags {
    display: none;
  }

  .card-title {
    font-size: 22px;
  }

  .submit-button {
    height: 44px;
  }
}

@media (max-height: 720px) and (min-width: 861px) {
  .login-shell {
    max-width: 420px;
    grid-template-columns: 1fr;
  }

  .brand-panel {
    display: none;
  }
}

@media (max-width: 860px) {
  .login-shell {
    grid-template-columns: 1fr;
  }

  .brand-panel {
    display: none;
  }
}
</style>

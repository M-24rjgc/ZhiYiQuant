<template>
  <div :class="footerCls">
    <global-footer class="footer custom-render">
      <template v-slot:links>
        <a @click="showLegal = true" style="cursor: pointer;">{{ $t('user.login.legal.title') }} © 2025-2026 ZhiYiQuant</a>
      </template>
    </global-footer>

    <a-modal :visible="showLegal" :title="$t('user.login.legal.title')" :footer="null" @cancel="showLegal = false">
      <div :class="['legal-content', { 'legal-content-dark': isDarkTheme }]">
        {{ $t('user.login.legal.content') }}
      </div>
      <div style="margin-top: 12px; text-align: right;">
        <a-button type="primary" @click="showLegal = false">OK</a-button>
      </div>
    </a-modal>
  </div>
</template>

<script>
import { GlobalFooter } from '@ant-design-vue/pro-layout'
import { baseMixin } from '@/store/app-mixin'

export default {
  name: 'ProGlobalFooter',
  components: {
    GlobalFooter
  },
  mixins: [baseMixin],
  data () {
    return {
      showLegal: false
    }
  },
  computed: {
    // 判断是否为暗黑主题
    isDarkTheme () {
      return this.navTheme === 'dark' || this.navTheme === 'realdark'
    },
    // Footer 容器类名
    footerCls () {
      return {
        'footer-wrapper': true,
        'footer-wrapper-dark': this.isDarkTheme
      }
    }
  }
}
</script>

<style lang="less">
/* 不使用 scoped，直接覆盖全局样式 */
.footer-wrapper {
  /* 调整内间距 */
  .ant-pro-global-footer {
    padding: 4px 16px 8px;
    margin: 0;
  }
  .ant-pro-global-footer-links {
    margin-bottom: 2px;
    padding: 0;
  }
  .ant-pro-global-footer-copyright {
    margin-top: 2px;
    padding: 0;
  }
}

/* 浅色主题（默认）- 确保文字是深色的 */
.footer-wrapper {
  .ant-pro-global-footer {
    background: transparent !important;
    color: rgba(0, 0, 0, 0.65) !important;
  }

  /* 链接颜色 */
  .ant-pro-global-footer-links {
    a {
      color: rgba(0, 0, 0, 0.65) !important;

      &:hover {
        color: #1890ff !important;
      }
    }
  }

  /* 版权文字颜色 */
  .ant-pro-global-footer-copyright {
    color: rgba(0, 0, 0, 0.65) !important;
  }
}

/* 浅色主题（默认） */
.legal-content {
  white-space: pre-wrap;
  line-height: 1.7;
  color: rgba(0, 0, 0, 0.85);
}

/* 暗黑主题 - 通过组件外层类名控制 */
.footer-wrapper-dark {
  .ant-pro-global-footer {
    background: transparent !important;
    color: rgba(255, 255, 255, 0.65) !important;
    border-top: none !important;
  }

  /* 链接颜色 */
  .ant-pro-global-footer-links {
    a {
      color: rgba(255, 255, 255, 0.65) !important;

      &:hover {
        color: #1890ff !important;
      }
    }
  }

  /* 版权文字颜色 */
  .ant-pro-global-footer-copyright {
    color: rgba(255, 255, 255, 0.65) !important;
  }

  /* 弹窗内容颜色 */
  .legal-content {
    color: rgba(255, 255, 255, 0.85) !important;
  }
}
</style>

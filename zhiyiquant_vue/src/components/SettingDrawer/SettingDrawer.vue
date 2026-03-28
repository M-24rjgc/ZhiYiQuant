<template>
  <div class="setting-drawer">
    <a-drawer
      width="300"
      placement="right"
      @close="onClose"
      :closable="true"
      :visible="visible"
      :get-container="false"
    >
      <div class="setting-drawer-index-content">

        <div :style="{ marginBottom: '24px' }">
          <h3 class="setting-drawer-index-title">{{ $t('app.setting.pagestyle') }}</h3>

          <div class="setting-drawer-index-blockChecbox">
            <a-tooltip>
              <template slot="title">
                {{ $t('app.setting.pagestyle.dark') }}
              </template>
              <div class="setting-drawer-index-item" @click="handleMenuTheme('dark')">
                <img src="https://gw.alipayobjects.com/zos/rmsportal/LCkqqYNmvBEbokSDscrm.svg" alt="dark">
                <div class="setting-drawer-index-selectIcon" v-if="currentNavTheme === 'dark'">
                  <a-icon type="check"/>
                </div>
              </div>
            </a-tooltip>

            <a-tooltip>
              <template slot="title">
                {{ $t('app.setting.pagestyle.light') }}
              </template>
              <div class="setting-drawer-index-item" @click="handleMenuTheme('light')">
                <img src="https://gw.alipayobjects.com/zos/rmsportal/jpRkZQMyYRryryPNtyIC.svg" alt="light">
                <div class="setting-drawer-index-selectIcon" v-if="currentNavTheme !== 'dark'">
                  <a-icon type="check"/>
                </div>
              </div>
            </a-tooltip>
          </div>
        </div>

        <div :style="{ marginBottom: '24px' }">
          <h3 class="setting-drawer-index-title">{{ $t('app.setting.themecolor') }}</h3>

          <div style="height: 20px">
            <a-tooltip class="setting-drawer-theme-color-colorBlock" v-for="(item, index) in colorList" :key="index">
              <template slot="title">
                {{ item.key }}
              </template>
              <a-tag :color="item.color" @click="changeColor(item.color)">
                <a-icon type="check" v-if="item.color === currentPrimaryColor"></a-icon>
              </a-tag>
            </a-tooltip>

          </div>
        </div>
        <a-divider />

        <!-- Navigation Mode and Content Width are hidden -->
        <div :style="{ marginBottom: '24px', display: 'none' }">
          <h3 class="setting-drawer-index-title">{{ $t('app.setting.navigationmode') }}</h3>

          <div class="setting-drawer-index-blockChecbox">
            <a-tooltip>
              <template slot="title">
                {{ $t('app.setting.sidemenu.nav') }}
              </template>
              <div class="setting-drawer-index-item" @click="handleLayout('sidemenu')">
                <img src="https://gw.alipayobjects.com/zos/rmsportal/JopDzEhOqwOjeNTXkoje.svg" alt="sidemenu">
                <div class="setting-drawer-index-selectIcon" v-if="layoutMode === 'sidemenu'">
                  <a-icon type="check"/>
                </div>
              </div>
            </a-tooltip>

            <a-tooltip>
              <template slot="title">
                {{ $t('app.setting.topmenu.nav') }}
              </template>
              <div class="setting-drawer-index-item" @click="handleLayout('topmenu')">
                <img src="https://gw.alipayobjects.com/zos/rmsportal/KDNDBbriJhLwuqMoxcAr.svg" alt="topmenu">
                <div class="setting-drawer-index-selectIcon" v-if="layoutMode !== 'sidemenu'">
                  <a-icon type="check"/>
                </div>
              </div>
            </a-tooltip>
          </div>
          <div :style="{ marginTop: '24px' }">
            <a-list :split="false">
              <a-list-item>
                <a-tooltip slot="actions">
                  <template slot="title">
                    {{ $t('app.setting.content-width.tooltip') }}
                  </template>
                  <a-select size="small" style="width: 80px;" :defaultValue="currentContentWidth" @change="handleContentWidthChange">
                    <a-select-option value="Fixed">{{ $t('app.setting.content-width.fixed') }}</a-select-option>
                    <a-select-option value="Fluid" v-if="layoutMode !== 'sidemenu'">{{ $t('app.setting.content-width.fluid') }}</a-select-option>
                  </a-select>
                </a-tooltip>
                <a-list-item-meta>
                  <div slot="title">{{ $t('app.setting.content-width') }}</div>
                </a-list-item-meta>
              </a-list-item>
              <a-list-item>
                <a-switch slot="actions" size="small" :defaultChecked="currentFixedHeader" @change="handleFixedHeader" />
                <a-list-item-meta>
                  <div slot="title">{{ $t('app.setting.fixedheader') }}</div>
                </a-list-item-meta>
              </a-list-item>
              <a-list-item>
                <a-switch slot="actions" size="small" :disabled="!currentFixedHeader" :defaultChecked="currentAutoHideHeader" @change="handleFixedHeaderHidden" />
                <a-list-item-meta>
                  <a-tooltip slot="title" placement="left">
                    <template slot="title">{{ $t('app.setting.fixedheader.tooltip') }}</template>
                    <div :style="{ opacity: !currentFixedHeader ? '0.5' : '1' }">{{ $t('app.setting.autoHideHeader') }}</div>
                  </a-tooltip>
                </a-list-item-meta>
              </a-list-item>
              <a-list-item >
                <a-switch slot="actions" size="small" :disabled="(layoutMode === 'topmenu')" :defaultChecked="fixSiderbar" @change="handleFixSiderbar" />
                <a-list-item-meta>
                  <div slot="title" :style="{ textDecoration: layoutMode === 'topmenu' ? 'line-through' : 'unset' }">{{ $t('app.setting.fixedsidebar') }}</div>
                </a-list-item-meta>
              </a-list-item>
            </a-list>
          </div>
        </div>
        <a-divider />

        <div :style="{ marginBottom: '24px' }">
          <h3 class="setting-drawer-index-title">{{ $t('app.setting.othersettings') }}</h3>
          <div>
            <a-list :split="false">
              <a-list-item>
                <a-switch slot="actions" size="small" :defaultChecked="currentColorWeak" @change="onColorWeak" />
                <a-list-item-meta>
                  <div slot="title">{{ $t('app.setting.weakmode') }}</div>
                </a-list-item-meta>
              </a-list-item>
              <a-list-item>
                <a-switch slot="actions" size="small" :defaultChecked="currentMultiTab" @change="onMultiTab" />
                <a-list-item-meta>
                  <div slot="title">{{ $t('app.setting.multitab') }}</div>
                </a-list-item-meta>
              </a-list-item>
            </a-list>
          </div>
        </div>
        <a-divider />
        <!-- <div :style="{ marginBottom: '24px' }">
          <a-button
            @click="doCopy"
            icon="copy"
            block
          >拷贝设置</a-button>
        </div> -->
      </div>
    </a-drawer>
  </div>
</template>

<script>
import SettingItem from './SettingItem'
import config from '@/config/defaultSettings'
import { updateTheme, updateColorWeak, getColorList } from './settingConfig'
import { baseMixin } from '@/store/app-mixin'

export default {
  components: {
    SettingItem
  },
  props: {
    settings: {
      type: Object,
      default: () => ({})
    }
  },
  mixins: [baseMixin],
  data () {
    return {
      visible: false
    }
  },
  computed: {
    colorList () {
      return getColorList()
    },
    layoutMode () {
      return this.settings.layout || this.layout || 'sidemenu'
    },
    fixSiderbar () {
      return this.settings.fixSiderbar !== undefined ? this.settings.fixSiderbar : (this.fixedSidebar || false)
    },
    currentNavTheme () {
      return this.settings.theme || this.navTheme || 'light'
    },
    currentPrimaryColor () {
      return this.settings.primaryColor || this.primaryColor || '#1890FF'
    },
    currentFixedHeader () {
      return this.settings.fixedHeader !== undefined ? this.settings.fixedHeader : (this.fixedHeader || false)
    },
    currentContentWidth () {
      return this.settings.contentWidth || this.contentWidth || 'Fluid'
    },
    currentAutoHideHeader () {
      return this.settings.autoHideHeader !== undefined ? this.settings.autoHideHeader : (this.autoHideHeader || false)
    },
    currentColorWeak () {
      return this.settings.colorWeak !== undefined ? this.settings.colorWeak : (this.colorWeak || false)
    },
    currentMultiTab () {
      return this.settings.multiTab !== undefined ? this.settings.multiTab : (this.multiTab || false)
    }
  },
  watch: {

  },
  mounted () {
    // 初始化时静默更新主题色，不显示消息
    updateTheme(this.currentPrimaryColor, true)
    if (this.currentColorWeak !== config.colorWeak) {
      updateColorWeak(this.currentColorWeak)
    }
  },
  methods: {
    showDrawer () {
      this.visible = true
    },
    onClose () {
      this.visible = false
    },
    toggle () {
      this.visible = !this.visible
    },
    onColorWeak (checked) {
      this.$emit('change', { type: 'colorWeak', value: checked })
      updateColorWeak(checked)
    },
    onMultiTab (checked) {
      this.$emit('change', { type: 'multiTab', value: checked })
    },
    handleMenuTheme (theme) {
      this.$emit('change', { type: 'theme', value: theme })
    },
    doCopy () {
      // get current settings from mixin or this.$store.state.app, pay attention to the property name
      const text = `export default {
  primaryColor: '${this.currentPrimaryColor}', // primary color of ant design
  navTheme: '${this.currentNavTheme}', // theme for nav menu
  layout: '${this.layoutMode}', // nav menu position: sidemenu or topmenu
  contentWidth: '${this.currentContentWidth}', // layout of content: Fluid or Fixed, only works when layout is topmenu
  fixedHeader: ${this.currentFixedHeader}, // sticky header
  fixSiderbar: ${this.fixSiderbar}, // sticky siderbar
  autoHideHeader: ${this.currentAutoHideHeader}, //  auto hide header
  colorWeak: ${this.currentColorWeak},
  multiTab: ${this.currentMultiTab},
  production: process.env.NODE_ENV === 'production' && process.env.VUE_APP_PREVIEW !== 'true'
}`
      this.$copyText(text).then(message => {
        this.$message.success(this.$t('app.setting.copy.success'))
      }).catch(() => {
        this.$message.error(this.$t('app.setting.copy.fail'))
      })
    },
    handleLayout (mode) {
      this.$emit('change', { type: 'layout', value: mode })
      // 因为顶部菜单不能固定左侧菜单栏，所以强制关闭
      if (mode === 'topmenu') {
        this.$emit('change', { type: 'fixSiderbar', value: false })
      }
    },
    handleContentWidthChange (type) {
      this.$emit('change', { type: 'contentWidth', value: type })
    },
    changeColor (color) {
      if (this.currentPrimaryColor !== color) {
        this.$emit('change', { type: 'primaryColor', value: color })
        updateTheme(color)
      }
    },
    handleFixedHeader (fixed) {
      this.$emit('change', { type: 'fixedHeader', value: fixed })
    },
    handleFixedHeaderHidden (autoHidden) {
      this.$emit('change', { type: 'autoHideHeader', value: autoHidden })
    },
    handleFixSiderbar (fixed) {
      if (this.layoutMode === 'topmenu') {
        this.$emit('change', { type: 'fixSiderbar', value: false })
        return
      }
      this.$emit('change', { type: 'fixSiderbar', value: fixed })
    }
  }
}
</script>

<style lang="less" scoped>
  /* 隐藏所有可能的悬浮按钮 */
  :deep(.ant-drawer-handle),
  :deep(.setting-drawer-index-handle) {
    display: none !important;
  }

  .setting-drawer-index-content {

    .setting-drawer-index-blockChecbox {
      display: flex;

      .setting-drawer-index-item {
        margin-right: 16px;
        position: relative;
        border-radius: 4px;
        cursor: pointer;

        img {
          width: 48px;
        }

        .setting-drawer-index-selectIcon {
          position: absolute;
          top: 0;
          right: 0;
          width: 100%;
          padding-top: 15px;
          padding-left: 24px;
          height: 100%;
          color: #1890ff;
          font-size: 14px;
          font-weight: 700;
        }
      }
    }
    .setting-drawer-theme-color-colorBlock {
      width: 20px;
      height: 20px;
      border-radius: 2px;
      float: left;
      cursor: pointer;
      margin-right: 8px;
      padding-left: 0px;
      padding-right: 0px;
      text-align: center;
      color: #fff;
      font-weight: 700;

      i {
        font-size: 14px;
      }
    }
  }

</style>

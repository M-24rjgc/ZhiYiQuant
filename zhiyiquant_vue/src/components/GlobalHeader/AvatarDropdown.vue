<template>
  <a-dropdown v-if="currentUser && currentUser.name" placement="bottomRight">
    <span class="ant-pro-account-avatar">
      <a-avatar size="small" :src="currentUser.avatar" class="antd-pro-global-header-index-avatar" />
      <span>{{ currentUser.name }}</span>
    </span>
    <template #overlay>
      <a-menu class="ant-pro-drop-down menu" :selected-keys="[]">
        <a-menu-item key="profile" @click="handleProfile">
          <a-icon type="user" />
          {{ $t('menu.profile') || 'My Profile' }}
        </a-menu-item>
        <a-menu-divider />
        <a-menu-item key="logout" @click="handleLogout">
          <a-icon type="logout" />
          {{ $t('menu.account.logout') }}
        </a-menu-item>
      </a-menu>
    </template>
  </a-dropdown>
  <span v-else>
    <a-spin size="small" :style="{ marginLeft: 8, marginRight: 8 }" />
  </span>
</template>

<script>
import { Modal } from 'ant-design-vue'

export default {
  name: 'AvatarDropdown',
  props: {
    currentUser: {
      type: Object,
      default: () => null
    },
    menu: {
      type: Boolean,
      default: true
    }
  },
  methods: {
    handleProfile () {
      this.$router.push({ name: 'Profile' })
    },
    handleLogout (e) {
      Modal.confirm({
        title: this.$t('layouts.usermenu.dialog.title'),
        content: this.$t('layouts.usermenu.dialog.content'),
        onOk: () => {
          // return new Promise((resolve, reject) => {
          //   setTimeout(Math.random() > 0.5 ? resolve : reject, 1500)
          // }).catch(() => console.log('Oops errors!'))
          return this.$store.dispatch('Logout').then(() => {
            this.$router.push({ name: 'login' })
          })
        },
        onCancel () {}
      })
    }
  }
}
</script>

<style lang="less">
.ant-pro-drop-down {
  .action {
    margin-right: 8px;
  }
  .ant-dropdown-menu-item {
    min-width: 160px;
  }
}

/* 暗黑主题 - 下拉菜单样式 */
body.dark .ant-dropdown-menu,
body.realdark .ant-dropdown-menu,
.ant-layout.dark .ant-dropdown-menu,
.ant-layout.realdark .ant-dropdown-menu,
.ant-pro-layout.dark .ant-dropdown-menu,
.ant-pro-layout.realdark .ant-dropdown-menu {
  background-color: #1f1f1f;
  border: 1px solid #303030;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);

  .ant-dropdown-menu-item {
    color: rgba(255, 255, 255, 0.85);

    &:hover,
    &.ant-dropdown-menu-item-selected {
      background-color: #262626;
      color: #1890ff;
    }

    .anticon {
      color: rgba(255, 255, 255, 0.85);
    }
  }

  .ant-dropdown-menu-item-divider {
    background-color: #303030;
  }
}
</style>

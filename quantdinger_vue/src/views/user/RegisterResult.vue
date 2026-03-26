<template>
  <div class="register-result">
    <a-result
      status="success"
      :title="$t('user.register-result.msg', { email: '-' })"
    >
      <template #extra>
        <a-button type="primary" @click="$router.push({ path: '/' })">
          {{ $t('user.register-result.back-home') || '返回首页' }}
        </a-button>
      </template>
    </a-result>
  </div>
</template>

<script>
export default {
  name: 'RegisterResult'
}
</script>

<style scoped>
.register-result {
  padding: 24px;
}
</style>

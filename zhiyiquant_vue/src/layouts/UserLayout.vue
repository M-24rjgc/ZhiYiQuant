<template>
  <div id="userLayout" :class="['user-layout-wrapper', isMobile && 'mobile']">
    <div class="container">
      <div class="fx-layer" aria-hidden="true">
        <div class="fx-gradient"></div>
        <div class="fx-grid"></div>
      </div>
      <div class="user-layout-lang">
        <select-lang class="select-lang-trigger" />
      </div>
      <div class="user-layout-content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script>
import { deviceMixin } from '@/store/device-mixin'
import SelectLang from '@/components/SelectLang'

export default {
  name: 'UserLayout',
  components: {
    SelectLang
  },
  mixins: [deviceMixin],
  mounted () {
    document.body.classList.add('userLayout')
  },
  beforeDestroy () {
    document.body.classList.remove('userLayout')
  }
}
</script>

<style lang="less" scoped>
#userLayout.user-layout-wrapper {
  min-height: 100dvh;

  &.mobile {
    .container {
      padding: 12px 10px;
    }
  }

  .container {
    width: 100%;
    min-height: 100dvh;
    padding: clamp(12px, 2.2vh, 20px);
    box-sizing: border-box;
    background: linear-gradient(135deg, #edf5f9 0%, #f6fbfd 48%, #f2f3ff 100%);
    position: relative;
    overflow: hidden;

    .fx-layer {
      position: absolute;
      inset: 0;
      overflow: hidden;
      z-index: 0;
      pointer-events: none;

      .fx-gradient {
        position: absolute;
        inset: -10% -8% -12% -8%;
        background:
          radial-gradient(640px 360px at 14% 22%, rgba(53, 194, 214, 0.22), transparent 68%),
          radial-gradient(520px 320px at 86% 16%, rgba(132, 156, 255, 0.16), transparent 72%),
          radial-gradient(680px 420px at 50% 90%, rgba(0, 176, 163, 0.12), transparent 72%);
        filter: blur(28px);
        animation: fxFloat 18s ease-in-out infinite alternate;
        transform: translateZ(0);
      }

      .fx-grid {
        position: absolute;
        inset: 0;
        background-image:
          linear-gradient(rgba(18, 78, 98, 0.05) 1px, transparent 1px),
          linear-gradient(90deg, rgba(18, 78, 98, 0.05) 1px, transparent 1px);
        background-size: 48px 48px, 48px 48px;
        background-position: 0 0, 0 0;
        opacity: 0.45;
        animation: gridDrift 40s linear infinite;
      }
    }

    .user-layout-lang {
      position: absolute;
      top: 10px;
      right: 14px;
      z-index: 2;

      .select-lang-trigger {
        cursor: pointer;
        width: 38px;
        height: 38px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 17px;
        border-radius: 12px;
        color: #214a59;
        background: rgba(255, 255, 255, 0.6);
        backdrop-filter: blur(12px);
        box-shadow: 0 10px 30px rgba(26, 58, 72, 0.08);
      }
    }

    .user-layout-content {
      min-height: calc(100dvh - 24px);
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      z-index: 1;
    }

    a {
      text-decoration: none;
    }
  }
}

@keyframes fxFloat {
  0% { transform: translate3d(-2%, -1%, 0) scale(1); }
  50% { transform: translate3d(1%, 2%, 0) scale(1.02); }
  100% { transform: translate3d(3%, -2%, 0) scale(1.04); }
}

@keyframes gridDrift {
  0% { background-position: 0 0, 0 0; transform: rotate(0deg); }
  50% { background-position: 22px 22px, 22px 22px; }
  100% { background-position: 44px 44px, 44px 44px; transform: rotate(0.01turn); }
}
</style>

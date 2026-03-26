<template>
  <a-card
    hoverable
    class="indicator-card"
    :body-style="{ padding: '12px' }"
    @click="$emit('click', indicator)"
  >
    <!-- 预览图 / 默认生成封面 -->
    <div class="card-cover" :style="coverStyle">
      <img
        v-if="indicator.preview_image && !imageError"
        :src="indicator.preview_image"
        :alt="indicator.name"
        @error="handleImageError"
      />
      <!-- 默认封面：使用渐变背景 + 标题 -->
      <div v-else class="default-cover" :style="{ background: coverGradient }">
        <span class="cover-title">{{ indicatorInitials }}</span>
        <span class="cover-subtitle">{{ indicator.name }}</span>
      </div>
      <div class="price-tag" :class="isPaid ? 'paid' : 'free'">
        {{ isPaid ? `${indicator.price} ${$t('community.credits')}` : $t('community.free') }}
      </div>
      <div v-if="indicator.is_own" class="own-tag">
        {{ $t('community.myIndicator') }}
      </div>
      <div v-else-if="indicator.is_purchased" class="purchased-tag">
        <a-icon type="check-circle" /> {{ $t('community.purchased') }}
      </div>
    </div>

    <!-- 内容 -->
    <div class="card-content">
      <h3 class="card-title" :title="indicator.name">{{ indicator.name }}</h3>
      <p class="card-desc">{{ indicator.description || $t('community.noDescription') }}</p>

      <!-- 作者信息 -->
      <div class="card-author">
        <a-avatar :src="indicator.author.avatar" :size="24" />
        <span class="author-name">{{ indicator.author.nickname || indicator.author.username }}</span>
      </div>

      <!-- 统计信息 -->
      <div class="card-stats">
        <span class="stat-item">
          <a-icon type="download" />
          {{ indicator.purchase_count || 0 }}
        </span>
        <span class="stat-item">
          <a-icon type="star" theme="filled" :style="{ color: '#faad14' }" />
          {{ formatRating(indicator.avg_rating) }}
        </span>
        <span class="stat-item">
          <a-icon type="eye" />
          {{ indicator.view_count || 0 }}
        </span>
      </div>
    </div>
  </a-card>
</template>

<script>
// 预定义的渐变色方案
const GRADIENT_PRESETS = [
  'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
  'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
  'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
  'linear-gradient(135deg, #d299c2 0%, #fef9d7 100%)',
  'linear-gradient(135deg, #89f7fe 0%, #66a6ff 100%)',
  'linear-gradient(135deg, #fddb92 0%, #d1fdff 100%)',
  'linear-gradient(135deg, #9890e3 0%, #b1f4cf 100%)',
  'linear-gradient(135deg, #ebc0fd 0%, #d9ded8 100%)',
  'linear-gradient(135deg, #f6d365 0%, #fda085 100%)'
]

export default {
  name: 'IndicatorCard',
  props: {
    indicator: {
      type: Object,
      required: true
    }
  },
  data () {
    return {
      imageError: false
    }
  },
  computed: {
    isPaid () {
      return this.indicator.pricing_type !== 'free' && this.indicator.price > 0
    },
    // 根据指标 ID 生成固定的渐变色
    coverGradient () {
      const index = (this.indicator.id || 0) % GRADIENT_PRESETS.length
      return GRADIENT_PRESETS[index]
    },
    // 生成指标名称首字母
    indicatorInitials () {
      const name = this.indicator.name || 'I'
      // 如果是中文，取前两个字
      if (/[\u4e00-\u9fa5]/.test(name)) {
        return name.slice(0, 2)
      }
      // 如果是英文，取首字母大写
      const words = name.split(/\s+/)
      if (words.length >= 2) {
        return (words[0][0] + words[1][0]).toUpperCase()
      }
      return name.slice(0, 2).toUpperCase()
    },
    coverStyle () {
      return {
        background: (!this.indicator.preview_image || this.imageError) ? this.coverGradient : '#f5f5f5'
      }
    }
  },
  methods: {
    formatRating (rating) {
      const r = parseFloat(rating) || 0
      return r > 0 ? r.toFixed(1) : '-'
    },
    handleImageError () {
      this.imageError = true
    }
  }
}
</script>

<style lang="less" scoped>
.indicator-card {
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s ease;
  height: 100%;
  display: flex;
  flex-direction: column;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  }

  .card-cover {
    position: relative;
    width: 100%;
    height: 140px;
    overflow: hidden;

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .default-cover {
      width: 100%;
      height: 100%;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: #fff;
      position: relative;
      overflow: hidden;

      // 添加装饰性圆圈
      &::before {
        content: '';
        position: absolute;
        top: -20%;
        right: -20%;
        width: 80%;
        height: 80%;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.1);
      }

      &::after {
        content: '';
        position: absolute;
        bottom: -30%;
        left: -20%;
        width: 60%;
        height: 60%;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.08);
      }

      .cover-title {
        font-size: 36px;
        font-weight: 700;
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        z-index: 1;
        letter-spacing: 2px;
      }

      .cover-subtitle {
        font-size: 12px;
        margin-top: 8px;
        opacity: 0.9;
        max-width: 80%;
        text-align: center;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        z-index: 1;
      }
    }

    .price-tag {
      position: absolute;
      top: 8px;
      right: 8px;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 600;
      z-index: 2;

      &.free {
        background: #52c41a;
        color: #fff;
      }

      &.paid {
        background: linear-gradient(135deg, #f5af19 0%, #f12711 100%);
        color: #fff;
      }
    }

    .own-tag,
    .purchased-tag {
      position: absolute;
      bottom: 8px;
      left: 8px;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      background: rgba(0, 0, 0, 0.6);
      color: #fff;
      z-index: 2;
    }

    .purchased-tag {
      background: rgba(82, 196, 26, 0.85);
    }
  }

  .card-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 4px 0;

    .card-title {
      font-size: 14px;
      font-weight: 600;
      margin: 0 0 6px 0;
      color: rgba(0, 0, 0, 0.85);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .card-desc {
      font-size: 12px;
      color: rgba(0, 0, 0, 0.45);
      margin: 0 0 8px 0;
      overflow: hidden;
      text-overflow: ellipsis;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      line-height: 1.5;
      min-height: 36px;
    }

    .card-author {
      display: flex;
      align-items: center;
      margin-bottom: 8px;

      .author-name {
        margin-left: 8px;
        font-size: 12px;
        color: rgba(0, 0, 0, 0.65);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    .card-stats {
      display: flex;
      gap: 12px;
      margin-top: auto;

      .stat-item {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 12px;
        color: rgba(0, 0, 0, 0.45);

        .anticon {
          font-size: 14px;
        }
      }
    }
  }
}

// 暗色主题适配
.theme-dark .indicator-card,
.dark-theme .indicator-card,
[data-theme='dark'] .indicator-card {
  background: #1f1f1f;
  border-color: #303030;

  .card-content {
    .card-title {
      color: rgba(255, 255, 255, 0.85);
    }

    .card-desc {
      color: rgba(255, 255, 255, 0.45);
    }

    .card-author .author-name {
      color: rgba(255, 255, 255, 0.65);
    }

    .card-stats .stat-item {
      color: rgba(255, 255, 255, 0.45);
    }
  }
}
</style>

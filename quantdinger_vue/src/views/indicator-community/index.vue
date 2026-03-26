<template>
  <div class="indicator-community-container" :class="{ 'theme-dark': isDarkTheme }">
    <!-- 管理员：标签切换 -->
    <a-tabs v-if="isAdmin" v-model="activeTab" class="admin-tabs" @change="handleTabChange">
      <a-tab-pane key="market" :tab="$t('community.title')">
        <!-- 市场内容在下方 -->
      </a-tab-pane>
      <a-tab-pane key="review">
        <template slot="tab">
          <a-badge :count="reviewStats.pending" :offset="[10, 0]">
            {{ $t('community.admin.reviewTab') }}
          </a-badge>
        </template>
      </a-tab-pane>
    </a-tabs>

    <!-- 顶部工具栏（市场模式） -->
    <div v-show="activeTab === 'market'" class="market-header">
      <div class="header-left">
        <h2 class="page-title">
          <a-icon type="shop" />
          {{ $t('community.title') }}
        </h2>
      </div>
      <div class="header-right">
        <!-- 搜索 -->
        <a-input-search
          v-model="filters.keyword"
          :placeholder="$t('community.searchPlaceholder')"
          style="width: 240px"
          allow-clear
          @search="handleSearch"
          @pressEnter="handleSearch"
        />
        <!-- 价格筛选 -->
        <a-radio-group v-model="filters.pricingType" button-style="solid" @change="handleFilterChange">
          <a-radio-button value="">{{ $t('community.all') }}</a-radio-button>
          <a-radio-button value="free">{{ $t('community.freeOnly') }}</a-radio-button>
          <a-radio-button value="paid">{{ $t('community.paidOnly') }}</a-radio-button>
        </a-radio-group>
        <!-- 排序 -->
        <a-select v-model="filters.sortBy" style="width: 140px" @change="handleFilterChange">
          <a-select-option value="newest">{{ $t('community.sortNewest') }}</a-select-option>
          <a-select-option value="hot">{{ $t('community.sortHot') }}</a-select-option>
          <a-select-option value="rating">{{ $t('community.sortRating') }}</a-select-option>
          <a-select-option value="price_asc">{{ $t('community.sortPriceLow') }}</a-select-option>
          <a-select-option value="price_desc">{{ $t('community.sortPriceHigh') }}</a-select-option>
        </a-select>
        <!-- 我的购买 -->
        <a-button type="link" @click="showMyPurchases = true">
          <a-icon type="shopping" />
          {{ $t('community.myPurchases') }}
        </a-button>
      </div>
    </div>

    <!-- 指标网格（市场模式） -->
    <template v-if="activeTab === 'market'">
      <a-spin :spinning="loading">
        <div v-if="indicators.length === 0 && !loading" class="empty-state">
          <a-empty :description="$t('community.noIndicators')">
            <a-button type="primary" @click="goToCreate">
              {{ $t('community.createFirst') }}
            </a-button>
          </a-empty>
        </div>
        <div v-else class="indicator-grid">
          <indicator-card
            v-for="item in indicators"
            :key="item.id"
            :indicator="item"
            @click="openDetail(item)"
          />
        </div>
      </a-spin>

      <!-- 分页 -->
      <div v-if="pagination.total > 0" class="pagination-wrapper">
        <a-pagination
          v-model="pagination.current"
          :total="pagination.total"
          :page-size="pagination.pageSize"
          :show-total="(total) => `${$t('community.total')} ${total} ${$t('community.items')}`"
          show-quick-jumper
          @change="handlePageChange"
        />
      </div>
    </template>

    <!-- 管理员审核区域 -->
    <template v-if="activeTab === 'review' && isAdmin">
      <div class="review-panel">
        <!-- 审核状态筛选 -->
        <div class="review-header">
          <a-radio-group v-model="reviewFilter" button-style="solid" @change="loadPendingIndicators">
            <a-radio-button value="pending">
              <a-badge :count="reviewStats.pending" :offset="[8, -2]" :number-style="{ backgroundColor: '#faad14' }">
                {{ $t('community.admin.pending') }}
              </a-badge>
            </a-radio-button>
            <a-radio-button value="approved">
              {{ $t('community.admin.approved') }} ({{ reviewStats.approved }})
            </a-radio-button>
            <a-radio-button value="rejected">
              {{ $t('community.admin.rejected') }} ({{ reviewStats.rejected }})
            </a-radio-button>
          </a-radio-group>
        </div>

        <!-- 审核列表 -->
        <a-spin :spinning="reviewLoading">
          <div v-if="pendingIndicators.length === 0 && !reviewLoading" class="empty-state">
            <a-empty :description="$t('community.admin.noItems')" />
          </div>
          <div v-else class="review-list">
            <div v-for="item in pendingIndicators" :key="item.id" class="review-item">
              <div class="review-item-header">
                <div class="item-info">
                  <span class="item-name">{{ item.name }}</span>
                  <a-tag v-if="item.pricing_type === 'free'" color="green">{{ $t('community.free') }}</a-tag>
                  <a-tag v-else color="orange">{{ item.price }} {{ $t('community.credits') }}</a-tag>
                  <a-tag :color="getStatusColor(item.review_status)">{{ getStatusText(item.review_status) }}</a-tag>
                </div>
                <div class="item-author">
                  <a-avatar :src="item.author.avatar" size="small" />
                  <span>{{ item.author.nickname || item.author.username }}</span>
                  <span class="item-time">{{ formatDate(item.created_at) }}</span>
                </div>
              </div>

              <div class="review-item-body">
                <div class="item-desc">{{ item.description || $t('community.admin.noDescription') }}</div>
                <div v-if="item.code" class="item-code">
                  <a-button type="link" size="small" @click="toggleCode(item.id)">
                    <a-icon :type="expandedCodes[item.id] ? 'up' : 'down'" />
                    {{ $t('community.admin.viewCode') }}
                  </a-button>
                  <pre v-if="expandedCodes[item.id]" class="code-preview">{{ item.code }}</pre>
                </div>
                <div v-if="item.review_note" class="review-note">
                  <a-icon type="info-circle" />
                  {{ $t('community.admin.note') }}: {{ item.review_note }}
                </div>
              </div>

              <div class="review-item-actions">
                <template v-if="item.review_status === 'pending'">
                  <a-button type="primary" size="small" @click="handleReview(item, 'approve')">
                    <a-icon type="check" />
                    {{ $t('community.admin.approve') }}
                  </a-button>
                  <a-button type="danger" size="small" @click="handleReview(item, 'reject')">
                    <a-icon type="close" />
                    {{ $t('community.admin.reject') }}
                  </a-button>
                </template>
                <template v-else-if="item.review_status === 'approved'">
                  <a-button size="small" @click="handleUnpublish(item)">
                    <a-icon type="stop" />
                    {{ $t('community.admin.unpublish') }}
                  </a-button>
                </template>
                <a-popconfirm
                  :title="$t('community.admin.deleteConfirm')"
                  @confirm="handleDelete(item)"
                >
                  <a-button type="link" size="small" class="delete-btn">
                    <a-icon type="delete" />
                    {{ $t('community.admin.delete') }}
                  </a-button>
                </a-popconfirm>
              </div>
            </div>
          </div>
        </a-spin>

        <!-- 审核分页 -->
        <div v-if="reviewPagination.total > 0" class="pagination-wrapper">
          <a-pagination
            v-model="reviewPagination.current"
            :total="reviewPagination.total"
            :page-size="reviewPagination.pageSize"
            :show-total="(total) => `${$t('community.total')} ${total} ${$t('community.items')}`"
            @change="handleReviewPageChange"
          />
        </div>
      </div>
    </template>

    <!-- 审核弹窗 -->
    <a-modal
      v-model="showReviewModal"
      :title="reviewAction === 'approve' ? $t('community.admin.approveTitle') : $t('community.admin.rejectTitle')"
      :ok-text="reviewAction === 'approve' ? $t('community.admin.approve') : $t('community.admin.reject')"
      :ok-button-props="{ props: { type: reviewAction === 'approve' ? 'primary' : 'danger' } }"
      @ok="submitReview"
    >
      <a-form layout="vertical">
        <a-form-item :label="$t('community.admin.noteLabel')">
          <a-textarea
            v-model="reviewNote"
            :placeholder="$t('community.admin.notePlaceholder')"
            :rows="3"
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 详情弹窗 -->
    <indicator-detail
      :visible="detailVisible"
      :indicator-id="selectedIndicatorId"
      :current-user-id="currentUserId"
      @close="detailVisible = false"
      @purchased="handlePurchased"
    />

    <!-- 我的购买弹窗 -->
    <a-modal
      v-model="showMyPurchases"
      :title="$t('community.myPurchases')"
      :footer="null"
      width="600px"
    >
      <a-spin :spinning="purchasesLoading">
        <div v-if="myPurchases.length === 0" class="empty-purchases">
          <a-empty :description="$t('community.noPurchases')" />
        </div>
        <a-list v-else :data-source="myPurchases" item-layout="horizontal">
          <a-list-item slot="renderItem" slot-scope="item">
            <a-list-item-meta>
              <template #title>
                <a @click="openDetailById(item.indicator.id)">{{ item.indicator.name }}</a>
              </template>
              <template #description>
                <div>{{ $t('community.purchasedFrom') }}: {{ item.seller.nickname }}</div>
                <div>{{ $t('community.purchaseTime') }}: {{ formatDate(item.purchase_time) }}</div>
              </template>
            </a-list-item-meta>
            <template #actions>
              <a-button type="link" size="small" @click="goToUse">
                {{ $t('community.useNow') }}
              </a-button>
            </template>
          </a-list-item>
        </a-list>
      </a-spin>
    </a-modal>
  </div>
</template>

<script>
import { mapState } from 'vuex'
import IndicatorCard from './components/IndicatorCard.vue'
import IndicatorDetail from './components/IndicatorDetail.vue'
import request from '@/utils/request'

export default {
  name: 'IndicatorCommunity',
  components: {
    IndicatorCard,
    IndicatorDetail
  },
  computed: {
    ...mapState({
      currentUserId: state => state.user.info?.id || state.user.info?.userId,
      userRole: state => state.user.info?.role,
      navTheme: state => state.app.theme
    }),
    isDarkTheme () {
      return this.navTheme === 'dark' || this.navTheme === 'realdark'
    },
    isAdmin () {
      if (!this.userRole) return false
      const roleId = this.userRole.id || this.userRole
      return roleId === 'admin'
    }
  },
  data () {
    return {
      loading: false,
      indicators: [],
      filters: {
        keyword: '',
        pricingType: '',
        sortBy: 'newest'
      },
      pagination: {
        current: 1,
        pageSize: 12,
        total: 0
      },
      detailVisible: false,
      selectedIndicatorId: null,
      showMyPurchases: false,
      purchasesLoading: false,
      myPurchases: [],
      // 管理员审核相关
      activeTab: 'market',
      reviewFilter: 'pending',
      reviewLoading: false,
      pendingIndicators: [],
      reviewPagination: {
        current: 1,
        pageSize: 20,
        total: 0
      },
      reviewStats: {
        pending: 0,
        approved: 0,
        rejected: 0
      },
      expandedCodes: {},
      // 审核弹窗
      showReviewModal: false,
      reviewAction: 'approve',
      reviewNote: '',
      reviewingIndicator: null
    }
  },
  watch: {
    showMyPurchases (val) {
      if (val) {
        this.loadMyPurchases()
      }
    },
    isAdmin: {
      immediate: true,
      handler (val) {
        if (val) {
          this.loadReviewStats()
        }
      }
    }
  },
  mounted () {
    this.loadIndicators()
  },
  methods: {
    async loadIndicators () {
      this.loading = true
      try {
        const res = await request({
          url: '/api/community/indicators',
          method: 'get',
          params: {
            page: this.pagination.current,
            page_size: this.pagination.pageSize,
            keyword: this.filters.keyword || undefined,
            pricing_type: this.filters.pricingType || undefined,
            sort_by: this.filters.sortBy
          }
        })
        if (res.code === 1) {
          this.indicators = res.data.items || []
          this.pagination.total = res.data.total || 0
        } else {
          this.$message.error(res.msg || this.$t('community.loadFailed'))
        }
      } catch (e) {
        console.error('Load indicators failed:', e)
        this.$message.error(this.$t('community.loadFailed'))
      } finally {
        this.loading = false
      }
    },

    async loadMyPurchases () {
      this.purchasesLoading = true
      try {
        const res = await request({
          url: '/api/community/my-purchases',
          method: 'get',
          params: { page: 1, page_size: 50 }
        })
        if (res.code === 1) {
          this.myPurchases = res.data.items || []
        }
      } catch (e) {
        console.error('Load purchases failed:', e)
      } finally {
        this.purchasesLoading = false
      }
    },

    handleSearch () {
      this.pagination.current = 1
      this.loadIndicators()
    },

    handleFilterChange () {
      this.pagination.current = 1
      this.loadIndicators()
    },

    handlePageChange (page) {
      this.pagination.current = page
      this.loadIndicators()
    },

    openDetail (indicator) {
      this.selectedIndicatorId = indicator.id
      this.detailVisible = true
    },

    openDetailById (id) {
      this.showMyPurchases = false
      this.selectedIndicatorId = id
      this.detailVisible = true
    },

    handlePurchased () {
      // 刷新列表
      this.loadIndicators()
    },

    goToCreate () {
      this.$router.push('/indicator-analysis')
    },

    goToUse () {
      this.showMyPurchases = false
      this.$router.push('/indicator-analysis')
    },

    formatDate (dateStr) {
      if (!dateStr) return '-'
      return new Date(dateStr).toLocaleString()
    },

    // ==================== 管理员审核方法 ====================

    handleTabChange (tab) {
      if (tab === 'review') {
        this.loadPendingIndicators()
        this.loadReviewStats()
      }
    },

    async loadReviewStats () {
      try {
        const res = await request({
          url: '/api/community/admin/review-stats',
          method: 'get'
        })
        if (res.code === 1) {
          this.reviewStats = res.data || { pending: 0, approved: 0, rejected: 0 }
        }
      } catch (e) {
        console.error('Load review stats failed:', e)
      }
    },

    async loadPendingIndicators () {
      this.reviewLoading = true
      try {
        const res = await request({
          url: '/api/community/admin/pending-indicators',
          method: 'get',
          params: {
            page: this.reviewPagination.current,
            page_size: this.reviewPagination.pageSize,
            review_status: this.reviewFilter
          }
        })
        if (res.code === 1) {
          this.pendingIndicators = res.data.items || []
          this.reviewPagination.total = res.data.total || 0
        }
      } catch (e) {
        console.error('Load pending indicators failed:', e)
        this.$message.error(this.$t('community.admin.loadFailed'))
      } finally {
        this.reviewLoading = false
      }
    },

    handleReviewPageChange (page) {
      this.reviewPagination.current = page
      this.loadPendingIndicators()
    },

    toggleCode (id) {
      this.$set(this.expandedCodes, id, !this.expandedCodes[id])
    },

    getStatusColor (status) {
      const colors = {
        pending: 'orange',
        approved: 'green',
        rejected: 'red'
      }
      return colors[status] || 'default'
    },

    getStatusText (status) {
      const texts = {
        pending: this.$t('community.admin.pending'),
        approved: this.$t('community.admin.approved'),
        rejected: this.$t('community.admin.rejected')
      }
      return texts[status] || status
    },

    handleReview (indicator, action) {
      this.reviewingIndicator = indicator
      this.reviewAction = action
      this.reviewNote = ''
      this.showReviewModal = true
    },

    async submitReview () {
      if (!this.reviewingIndicator) return

      try {
        const res = await request({
          url: `/api/community/admin/indicators/${this.reviewingIndicator.id}/review`,
          method: 'post',
          data: {
            action: this.reviewAction,
            note: this.reviewNote
          }
        })
        if (res.code === 1) {
          this.$message.success(this.$t('community.admin.reviewSuccess'))
          this.showReviewModal = false
          this.loadPendingIndicators()
          this.loadReviewStats()
        } else {
          this.$message.error(res.msg || this.$t('community.admin.reviewFailed'))
        }
      } catch (e) {
        console.error('Review failed:', e)
        this.$message.error(this.$t('community.admin.reviewFailed'))
      }
    },

    async handleUnpublish (indicator) {
      this.$confirm({
        title: this.$t('community.admin.unpublishConfirm'),
        content: this.$t('community.admin.unpublishHint'),
        okText: this.$t('community.admin.confirm'),
        cancelText: this.$t('community.admin.cancel'),
        onOk: async () => {
          try {
            const res = await request({
              url: `/api/community/admin/indicators/${indicator.id}/unpublish`,
              method: 'post',
              data: { note: '' }
            })
            if (res.code === 1) {
              this.$message.success(this.$t('community.admin.unpublishSuccess'))
              this.loadPendingIndicators()
              this.loadReviewStats()
            } else {
              this.$message.error(res.msg || this.$t('community.admin.unpublishFailed'))
            }
          } catch (e) {
            console.error('Unpublish failed:', e)
            this.$message.error(this.$t('community.admin.unpublishFailed'))
          }
        }
      })
    },

    async handleDelete (indicator) {
      try {
        const res = await request({
          url: `/api/community/admin/indicators/${indicator.id}`,
          method: 'delete'
        })
        if (res.code === 1) {
          this.$message.success(this.$t('community.admin.deleteSuccess'))
          this.loadPendingIndicators()
          this.loadReviewStats()
        } else {
          this.$message.error(res.msg || this.$t('community.admin.deleteFailed'))
        }
      } catch (e) {
        console.error('Delete failed:', e)
        this.$message.error(this.$t('community.admin.deleteFailed'))
      }
    }
  }
}
</script>

<style lang="less" scoped>
.indicator-community-container {
  padding: 24px;
  min-height: calc(100vh - 120px);
  background: #f5f5f5;

  .market-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding: 16px 20px;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

    .header-left {
      .page-title {
        margin: 0;
        font-size: 20px;
        font-weight: 600;

        .anticon {
          margin-right: 8px;
          color: #1890ff;
        }
      }
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 16px;
    }
  }

  .indicator-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 20px;
  }

  .empty-state {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 400px;
    background: #fff;
    border-radius: 8px;
  }

  .pagination-wrapper {
    display: flex;
    justify-content: center;
    margin-top: 32px;
    padding: 16px;
    background: #fff;
    border-radius: 8px;
  }

  .empty-purchases {
    padding: 40px 0;
  }

  // 管理员标签
  .admin-tabs {
    margin-bottom: 16px;
    padding: 0 20px;
    background: #fff;
    border-radius: 8px;
  }

  // 审核区域
  .review-panel {
    .review-header {
      margin-bottom: 20px;
      padding: 16px 20px;
      background: #fff;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    }

    .review-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .review-item {
      background: #fff;
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

      .review-item-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 12px;

        .item-info {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;

          .item-name {
            font-size: 16px;
            font-weight: 600;
          }
        }

        .item-author {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          color: #666;

          .item-time {
            color: #999;
          }
        }
      }

      .review-item-body {
        margin-bottom: 16px;

        .item-desc {
          color: #666;
          margin-bottom: 8px;
          line-height: 1.6;
        }

        .item-code {
          .code-preview {
            margin-top: 8px;
            padding: 12px;
            background: #f5f5f5;
            border-radius: 4px;
            font-size: 12px;
            max-height: 300px;
            overflow: auto;
            white-space: pre-wrap;
            word-break: break-all;
          }
        }

        .review-note {
          margin-top: 12px;
          padding: 8px 12px;
          background: #fff7e6;
          border-radius: 4px;
          color: #d46b08;
          font-size: 13px;

          .anticon {
            margin-right: 6px;
          }
        }
      }

      .review-item-actions {
        display: flex;
        gap: 12px;
        padding-top: 12px;
        border-top: 1px solid #f0f0f0;

        .delete-btn {
          color: #ff4d4f;
          margin-left: auto;
        }
      }
    }
  }
}

// 暗色主题
.indicator-community-container.theme-dark {
  background: #141414;

  .admin-tabs {
    background: #1f1f1f;

    /deep/ .ant-tabs-nav .ant-tabs-tab {
      color: rgba(255, 255, 255, 0.65);
      &.ant-tabs-tab-active {
        color: #40a9ff;
      }
    }
  }

  .review-panel {
    .review-header {
      background: #1f1f1f;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }

    .review-item {
      background: #1f1f1f;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);

      .item-name {
        color: rgba(255, 255, 255, 0.85);
      }

      .item-author {
        color: rgba(255, 255, 255, 0.45);

        .item-time {
          color: rgba(255, 255, 255, 0.35);
        }
      }

      .item-desc {
        color: rgba(255, 255, 255, 0.65);
      }

      .item-code .code-preview {
        background: #262626;
        color: rgba(255, 255, 255, 0.85);
      }

      .review-note {
        background: rgba(250, 173, 20, 0.1);
        color: #ffc53d;
      }

      .review-item-actions {
        border-color: #303030;
      }
    }
  }

  .market-header {
    background: #1f1f1f;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);

    .page-title {
      color: rgba(255, 255, 255, 0.85);
    }
  }

  .empty-state,
  .pagination-wrapper {
    background: #1f1f1f;
  }

  // 穿透子组件样式 - IndicatorCard
  /deep/ .indicator-card {
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

  // 修复搜索框、下拉框等组件的暗色样式
  /deep/ .ant-input {
    background: #262626;
    border-color: #434343;
    color: rgba(255, 255, 255, 0.85);

    &::placeholder {
      color: rgba(255, 255, 255, 0.35);
    }
  }

  /deep/ .ant-input-search-icon {
    color: rgba(255, 255, 255, 0.45);
  }

  /deep/ .ant-radio-group {
    .ant-radio-button-wrapper {
      background: #262626;
      border-color: #434343;
      color: rgba(255, 255, 255, 0.65);

      &:hover {
        color: #40a9ff;
      }

      &.ant-radio-button-wrapper-checked {
        background: #177ddc;
        border-color: #177ddc;
        color: #fff;
      }
    }
  }

  /deep/ .ant-select {
    .ant-select-selection {
      background: #262626;
      border-color: #434343;
      color: rgba(255, 255, 255, 0.85);
    }

    .ant-select-arrow {
      color: rgba(255, 255, 255, 0.45);
    }
  }

  /deep/ .ant-btn-link {
    color: #40a9ff;
  }

  /deep/ .ant-pagination {
    .ant-pagination-item {
      background: #262626;
      border-color: #434343;

      a {
        color: rgba(255, 255, 255, 0.85);
      }

      &.ant-pagination-item-active {
        background: #177ddc;
        border-color: #177ddc;

        a {
          color: #fff;
        }
      }
    }

    .ant-pagination-prev,
    .ant-pagination-next {
      .ant-pagination-item-link {
        background: #262626;
        border-color: #434343;
        color: rgba(255, 255, 255, 0.65);
      }
    }

    .ant-pagination-options-quick-jumper {
      color: rgba(255, 255, 255, 0.65);

      input {
        background: #262626;
        border-color: #434343;
        color: rgba(255, 255, 255, 0.85);
      }
    }

    .ant-pagination-total-text {
      color: rgba(255, 255, 255, 0.65);
    }
  }

  // 我的购买弹窗
  /deep/ .ant-modal-content {
    background: #1f1f1f;

    .ant-modal-header {
      background: #1f1f1f;
      border-color: #303030;

      .ant-modal-title {
        color: rgba(255, 255, 255, 0.85);
      }
    }

    .ant-modal-close-x {
      color: rgba(255, 255, 255, 0.45);
    }

    .ant-list-item-meta-title a {
      color: #40a9ff;
    }

    .ant-list-item-meta-description {
      color: rgba(255, 255, 255, 0.45);
    }

    .ant-list-item {
      border-color: #303030;
    }
  }
}

// 响应式
@media (max-width: 768px) {
  .indicator-community-container {
    padding: 12px;

    .market-header {
      flex-direction: column;
      gap: 16px;

      .header-right {
        flex-wrap: wrap;
        justify-content: center;
      }
    }

    .indicator-grid {
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 12px;
    }
  }
}
</style>

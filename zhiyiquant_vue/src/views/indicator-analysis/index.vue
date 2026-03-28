<template>
  <div class="indicator-analysis-page" :class="{ 'theme-dark': isDarkTheme }">
    <div class="page-toolbar">
      <div class="toolbar-group">
        <a-select v-model="selectedMarket" style="width: 140px" @change="loadHotSymbols">
          <a-select-option v-for="item in marketTypes" :key="item.value" :value="item.value">
            {{ item.label }}
          </a-select-option>
        </a-select>

        <a-select
          v-model="selectedSymbolValue"
          show-search
          allow-clear
          style="width: 320px"
          :filter-option="false"
          placeholder="搜索标的"
          @search="handleSymbolSearch"
          @change="handleSymbolSelect"
        >
          <a-select-option
            v-for="item in symbolOptions"
            :key="`${item.market}:${item.symbol}`"
            :value="`${item.market}:${item.symbol}`"
          >
            {{ item.symbol }}<span v-if="item.name"> - {{ item.name }}</span>
          </a-select-option>
        </a-select>

        <div class="timeframe-group">
          <a-button
            v-for="item in timeframes"
            :key="item"
            size="small"
            :type="timeframe === item ? 'primary' : 'default'"
            @click="timeframe = item"
          >
            {{ item }}
          </a-button>
        </div>
      </div>

      <div class="toolbar-group">
        <a-button icon="reload" @click="loadIndicators">刷新指标</a-button>
        <a-button type="primary" icon="plus" @click="openCreateIndicator">新建指标</a-button>
      </div>
    </div>

    <div class="content-grid">
      <div class="chart-panel">
        <div class="chart-header" v-if="currentSymbol">
          <div class="symbol-block">
            <div class="symbol-name">{{ currentSymbol }}</div>
            <div class="symbol-market">{{ selectedMarket }}</div>
          </div>
          <div class="symbol-price" :class="priceChange >= 0 ? 'up' : 'down'">
            <div class="price-value">{{ currentPrice || '--' }}</div>
            <div class="price-change">{{ formatChange(priceChange) }}</div>
          </div>
        </div>

        <kline-chart
          :symbol="currentSymbol"
          :market="selectedMarket"
          :timeframe="timeframe"
          :theme="isDarkTheme ? 'dark' : 'light'"
          :activeIndicators="activeIndicators"
          :realtimeEnabled="true"
          :userId="currentUserId"
          @price-change="handlePriceChange"
        />
      </div>

      <div class="indicator-panel">
        <div class="panel-header">
          <h3>本地指标</h3>
          <span>{{ indicators.length }} 个</span>
        </div>

        <a-empty v-if="!loadingIndicators && indicators.length === 0" description="还没有指标">
          <a-button type="primary" @click="openCreateIndicator">创建第一个指标</a-button>
        </a-empty>

        <a-spin :spinning="loadingIndicators">
          <div class="indicator-list">
            <div v-for="indicator in indicators" :key="indicator.id" class="indicator-card">
              <div class="indicator-main" @click="toggleIndicator(indicator)">
                <div>
                  <div class="indicator-name">{{ indicator.name || '未命名指标' }}</div>
                  <div class="indicator-desc">{{ indicator.description || '本地自定义指标' }}</div>
                </div>
                <a-tag :color="isIndicatorActive(indicator.id) ? 'green' : 'default'">
                  {{ isIndicatorActive(indicator.id) ? '已加载' : '未加载' }}
                </a-tag>
              </div>

              <div class="indicator-actions">
                <a-button size="small" @click="toggleIndicator(indicator)">
                  {{ isIndicatorActive(indicator.id) ? '移除' : '加载' }}
                </a-button>
                <a-button size="small" @click="openEditIndicator(indicator)">编辑</a-button>
                <a-button size="small" @click="openBacktest(indicator)">回测</a-button>
                <a-button size="small" @click="openHistory(indicator)">历史</a-button>
                <a-popconfirm title="确定删除这个指标？" @confirm="deleteIndicator(indicator)">
                  <a-button size="small" type="danger">删除</a-button>
                </a-popconfirm>
              </div>
            </div>
          </div>
        </a-spin>
      </div>
    </div>

    <indicator-editor
      :visible="showEditor"
      :indicator="editingIndicator"
      :userId="currentUserId"
      @cancel="closeEditor"
      @save="handleEditorSave"
    />

    <backtest-modal
      :visible="showBacktestModal"
      :userId="currentUserId"
      :indicator="backtestIndicator"
      :symbol="currentSymbol"
      :market="selectedMarket"
      :timeframe="timeframe"
      @cancel="showBacktestModal = false"
    />

    <backtest-history-drawer
      :visible="showHistoryDrawer"
      :userId="currentUserId"
      :indicatorId="historyIndicator ? historyIndicator.id : null"
      :symbol="currentSymbol"
      :market="selectedMarket"
      :timeframe="timeframe"
      :isMobile="isMobile"
      @cancel="showHistoryDrawer = false"
      @view="handleViewRun"
    />

    <backtest-run-viewer
      :visible="showRunViewer"
      :run="selectedRun"
      @cancel="showRunViewer = false"
    />
  </div>
</template>

<script>
import request from '@/utils/request'
import { baseMixin } from '@/store/app-mixin'
import { getHotSymbols, getMarketTypes, searchSymbols } from '@/api/market'
import KlineChart from './components/KlineChart.vue'
import IndicatorEditor from './components/IndicatorEditor.vue'
import BacktestModal from './components/BacktestModal.vue'
import BacktestHistoryDrawer from './components/BacktestHistoryDrawer.vue'
import BacktestRunViewer from './components/BacktestRunViewer.vue'

export default {
  name: 'IndicatorAnalysis',
  components: {
    KlineChart,
    IndicatorEditor,
    BacktestModal,
    BacktestHistoryDrawer,
    BacktestRunViewer
  },
  mixins: [baseMixin],
  data () {
    return {
      selectedMarket: 'Crypto',
      selectedSymbolValue: '',
      currentSymbol: '',
      timeframe: '1D',
      marketTypes: [],
      symbolOptions: [],
      indicators: [],
      activeIndicators: [],
      loadingIndicators: false,
      showEditor: false,
      editingIndicator: null,
      showBacktestModal: false,
      backtestIndicator: null,
      showHistoryDrawer: false,
      historyIndicator: null,
      showRunViewer: false,
      selectedRun: null,
      currentPrice: '',
      priceChange: 0,
      isMobile: false
    }
  },
  computed: {
    isDarkTheme () {
      return this.navTheme === 'dark' || this.navTheme === 'realdark'
    },
    currentUserId () {
      const info = this.$store.getters.userInfo || {}
      return info.id || 1
    }
  },
  mounted () {
    this.checkMobile()
    window.addEventListener('resize', this.checkMobile)
    this.loadMarketTypes()
    this.loadHotSymbols()
    this.loadIndicators()
  },
  beforeDestroy () {
    window.removeEventListener('resize', this.checkMobile)
  },
  methods: {
    checkMobile () {
      this.isMobile = window.innerWidth < 960
    },
    formatChange (value) {
      const num = Number(value || 0)
      return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`
    },
    handlePriceChange (payload) {
      if (!payload) return
      this.currentPrice = payload.price || payload.close || '--'
      this.priceChange = Number(payload.changePercent || payload.change || 0)
    },
    async loadMarketTypes () {
      const res = await getMarketTypes()
      const items = (res && res.data) || []
      this.marketTypes = items.map(item => ({
        value: item.value || item.market || item,
        label: item.label || item.name || item.value || item
      }))
      if (!this.marketTypes.find(item => item.value === this.selectedMarket) && this.marketTypes[0]) {
        this.selectedMarket = this.marketTypes[0].value
      }
    },
    async loadHotSymbols () {
      this.selectedSymbolValue = ''
      this.currentSymbol = ''
      const res = await getHotSymbols({ market: this.selectedMarket, limit: 20 })
      this.symbolOptions = Array.isArray(res.data) ? res.data : []
    },
    async handleSymbolSearch (keyword) {
      const q = (keyword || '').trim()
      if (!q) {
        await this.loadHotSymbols()
        return
      }
      const res = await searchSymbols({ market: this.selectedMarket, keyword: q, limit: 20 })
      this.symbolOptions = Array.isArray(res.data) ? res.data : []
    },
    handleSymbolSelect (value) {
      if (!value) {
        this.currentSymbol = ''
        return
      }
      const [market, symbol] = String(value).split(':')
      this.selectedMarket = market || this.selectedMarket
      this.currentSymbol = symbol || ''
    },
    async loadIndicators () {
      this.loadingIndicators = true
      try {
        const res = await request({
          url: '/api/indicator/getIndicators',
          method: 'get',
          params: { userid: this.currentUserId }
        })
        this.indicators = Array.isArray(res.data) ? res.data.map(item => ({ ...item, type: 'python' })) : []
      } finally {
        this.loadingIndicators = false
      }
    },
    isIndicatorActive (indicatorId) {
      return this.activeIndicators.some(item => item.id === indicatorId)
    },
    async toggleIndicator (indicator) {
      const exists = this.isIndicatorActive(indicator.id)
      if (exists) {
        this.activeIndicators = this.activeIndicators.filter(item => item.id !== indicator.id)
        return
      }

      let indicatorParams = {}
      try {
        const res = await request({
          url: '/api/indicator/getIndicatorParams',
          method: 'get',
          params: { id: indicator.id }
        })
        const params = (res && res.data && res.data.params) || []
        indicatorParams = params.reduce((acc, item) => {
          acc[item.name] = item.default
          return acc
        }, {})
      } catch (e) {
        indicatorParams = {}
      }

      this.activeIndicators = this.activeIndicators.concat({
        ...indicator,
        indicator_params: indicatorParams
      })
    },
    openCreateIndicator () {
      this.editingIndicator = null
      this.showEditor = true
    },
    openEditIndicator (indicator) {
      this.editingIndicator = indicator
      this.showEditor = true
    },
    closeEditor () {
      this.showEditor = false
      this.editingIndicator = null
    },
    async handleEditorSave (payload) {
      await request({
        url: '/api/indicator/saveIndicator',
        method: 'post',
        data: payload
      })
      this.$message.success('指标已保存')
      this.closeEditor()
      await this.loadIndicators()
    },
    async deleteIndicator (indicator) {
      await request({
        url: '/api/indicator/deleteIndicator',
        method: 'post',
        data: { id: indicator.id, userid: this.currentUserId }
      })
      this.$message.success('指标已删除')
      this.activeIndicators = this.activeIndicators.filter(item => item.id !== indicator.id)
      await this.loadIndicators()
    },
    openBacktest (indicator) {
      if (!this.currentSymbol) {
        this.$message.warning('请先选择标的')
        return
      }
      this.backtestIndicator = indicator
      this.showBacktestModal = true
    },
    openHistory (indicator) {
      this.historyIndicator = indicator
      this.showHistoryDrawer = true
    },
    handleViewRun (run) {
      this.selectedRun = run
      this.showRunViewer = true
    }
  }
}
</script>

<style lang="less" scoped>
.indicator-analysis-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.timeframe-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 16px;
}

.chart-panel,
.indicator-panel {
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 12px 30px rgba(16, 32, 40, 0.08);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.symbol-name {
  font-size: 22px;
  font-weight: 600;
}

.symbol-market {
  color: #7a8c94;
}

.symbol-price {
  text-align: right;
}

.symbol-price.up {
  color: #52c41a;
}

.symbol-price.down {
  color: #f5222d;
}

.price-value {
  font-size: 20px;
  font-weight: 600;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.indicator-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.indicator-card {
  border: 1px solid #edf1f4;
  border-radius: 12px;
  padding: 12px;
}

.indicator-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  cursor: pointer;
}

.indicator-name {
  font-weight: 600;
  color: #17333c;
}

.indicator-desc {
  margin-top: 4px;
  color: #7a8c94;
  font-size: 13px;
}

.indicator-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

@media (max-width: 1200px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}
</style>

<template>
  <a-drawer
    :title="$t('dashboard.indicator.backtest.historyTitle')"
    :visible="visible"
    :width="isMobile ? '100%' : 980"
    :maskClosable="true"
    @close="$emit('cancel')"
  >
    <div style="display:flex; gap: 12px; margin-bottom: 12px; align-items: center; flex-wrap: wrap;">
      <a-switch v-model="useCurrentFilters" />
      <span style="color:#8c8c8c;">
        {{ $t('dashboard.indicator.backtest.historyUseCurrent') }}
      </span>
      <a-button type="primary" :loading="loading" @click="loadRuns">
        {{ $t('dashboard.indicator.backtest.historyRefresh') }}
      </a-button>
      <a-button
        type="primary"
        :disabled="selectedRowKeys.length === 0"
        :loading="analyzing"
        @click="handleAIAnalyze"
      >
        {{ $t('dashboard.indicator.backtest.historyAIAnalyze') }}
      </a-button>
    </div>

    <div v-if="!useCurrentFilters" style="display:flex; gap: 12px; margin-bottom: 12px; align-items: center; flex-wrap: wrap;">
      <a-input v-model="filterSymbol" style="width: 220px" :placeholder="$t('dashboard.indicator.backtest.historyFilterSymbol')" />
      <a-select v-model="filterTimeframe" style="width: 140px" :placeholder="$t('dashboard.indicator.backtest.historyFilterTimeframe')" allowClear>
        <a-select-option v-for="tf in timeframes" :key="tf" :value="tf">{{ tf }}</a-select-option>
      </a-select>
      <a-button :loading="loading" @click="loadRuns">{{ $t('dashboard.indicator.backtest.historyApply') }}</a-button>
      <span style="color:#8c8c8c;">{{ filterLabel }}</span>
    </div>

    <a-table
      :columns="columns"
      :data-source="runs"
      :loading="loading"
      size="small"
      :pagination="{ pageSize: 10, size: 'small' }"
      rowKey="id"
      :scroll="{ x: 900 }"
      :rowSelection="{ selectedRowKeys: selectedRowKeys, onChange: onRowSelectionChange }"
    >
      <template slot="range" slot-scope="text, record">
        <span>{{ (record.start_date || '') }} ~ {{ (record.end_date || '') }}</span>
      </template>
      <template slot="status" slot-scope="text">
        <a-tag :color="text === 'success' ? 'green' : text === 'failed' ? 'red' : 'blue'">
          {{ text === 'success' ? $t('dashboard.indicator.backtest.historyStatusSuccess') : text === 'failed' ? $t('dashboard.indicator.backtest.historyStatusFailed') : text }}
        </a-tag>
      </template>
      <template slot="actions" slot-scope="text, record">
        <a-button type="link" size="small" :loading="detailLoadingId === record.id" @click="viewRun(record)">
          {{ $t('dashboard.indicator.backtest.historyView') }}
        </a-button>
      </template>
    </a-table>

    <a-empty v-if="!loading && runs.length === 0" :description="$t('dashboard.indicator.backtest.historyNoData')" />

    <a-modal
      :title="$t('dashboard.indicator.backtest.historyAIAnalyzeTitle')"
      :visible="showAIResult"
      :footer="null"
      :width="isMobile ? '100%' : 900"
      @cancel="showAIResult = false"
    >
      <div v-if="analyzing" style="padding: 12px 0;">
        <a-spin />
      </div>
      <div v-else style="white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;">
        {{ aiResult || $t('dashboard.indicator.backtest.historyNoAIResult') }}
      </div>
    </a-modal>
  </a-drawer>
</template>

<script>
import request from '@/utils/request'

export default {
  name: 'BacktestHistoryDrawer',
  props: {
    visible: { type: Boolean, default: false },
    userId: { type: [Number, String], default: 1 },
    indicatorId: { type: [Number, String], default: null },
    symbol: { type: String, default: '' },
    market: { type: String, default: '' },
    timeframe: { type: String, default: '' },
    isMobile: { type: Boolean, default: false }
  },
  data () {
    return {
      loading: false,
      detailLoadingId: null,
      analyzing: false,
      showAIResult: false,
      aiResult: '',
      useCurrentFilters: true,
      filterSymbol: '',
      filterTimeframe: '',
      timeframes: ['1m', '5m', '15m', '30m', '1H', '4H', '1D', '1W'],
      runs: [],
      columns: [],
      selectedRowKeys: []
    }
  },
  computed: {
    filterLabel () {
      const parts = []
      if (this.indicatorId) parts.push(`indicatorId=${this.indicatorId}`)
      const m = this.useCurrentFilters ? this.market : (this.market || '')
      const s = this.useCurrentFilters ? this.symbol : (this.filterSymbol || '')
      const tf = this.useCurrentFilters ? this.timeframe : (this.filterTimeframe || '')
      if (m) parts.push(`market=${m}`)
      if (s) parts.push(`symbol=${s}`)
      if (tf) parts.push(`timeframe=${tf}`)
      return parts.length ? parts.join(' | ') : ''
    }
  },
  watch: {
    visible (val) {
      if (val) {
        this.initColumns()
        this.useCurrentFilters = true
        this.filterSymbol = this.symbol || ''
        this.filterTimeframe = this.timeframe || ''
        this.selectedRowKeys = []
        this.aiResult = ''
        this.showAIResult = false
        this.loadRuns()
      }
    }
  },
  methods: {
    onRowSelectionChange (keys) {
      this.selectedRowKeys = keys || []
    },
    initColumns () {
      if (this.columns.length) return
      this.columns = [
        { title: this.$t('dashboard.indicator.backtest.historyRunId'), dataIndex: 'id', key: 'id', width: 90 },
        { title: this.$t('dashboard.indicator.backtest.historyCreatedAt'), dataIndex: 'created_at', key: 'created_at', width: 140 },
        { title: this.$t('dashboard.indicator.backtest.tradeDirection'), dataIndex: 'trade_direction', key: 'trade_direction', width: 90 },
        { title: this.$t('dashboard.indicator.backtest.leverage'), dataIndex: 'leverage', key: 'leverage', width: 90 },
        { title: this.$t('dashboard.indicator.backtest.historyRange'), key: 'range', width: 220, scopedSlots: { customRender: 'range' } },
        { title: this.$t('dashboard.indicator.backtest.historyStatus'), dataIndex: 'status', key: 'status', width: 90, scopedSlots: { customRender: 'status' } },
        { title: this.$t('dashboard.indicator.backtest.historyActions'), key: 'actions', width: 90, scopedSlots: { customRender: 'actions' } }
      ]
    },
    async loadRuns () {
      if (!this.userId) return
      this.loading = true
      try {
        const symbol = this.useCurrentFilters ? this.symbol : (this.filterSymbol || '')
        const timeframe = this.useCurrentFilters ? this.timeframe : (this.filterTimeframe || '')
        const market = this.market || ''
        const res = await request({
          url: '/api/indicator/backtest/history',
          method: 'get',
          params: {
            userid: this.userId,
            limit: 100,
            offset: 0,
            indicatorId: this.indicatorId,
            symbol,
            market,
            timeframe
          }
        })
        if (res && res.code === 1 && Array.isArray(res.data)) {
          this.runs = res.data
        } else {
          this.runs = []
        }
      } finally {
        this.loading = false
      }
    },
    async viewRun (record) {
      if (!record || !record.id) return
      this.detailLoadingId = record.id
      try {
        const res = await request({
          url: '/api/indicator/backtest/get',
          method: 'get',
          params: { userid: this.userId, runId: record.id }
        })
        if (res && res.code === 1 && res.data) {
          this.$emit('view', res.data)
        }
      } finally {
        this.detailLoadingId = null
      }
    },
    async handleAIAnalyze () {
      if (!this.userId || !this.selectedRowKeys.length) return
      this.analyzing = true
      this.showAIResult = true
      this.aiResult = ''
      try {
        const lang = (this.$i18n && this.$i18n.locale) ? this.$i18n.locale : 'zh-CN'
        const res = await request({
          url: '/api/indicator/backtest/aiAnalyze',
          method: 'post',
          data: { userid: this.userId, runIds: this.selectedRowKeys, lang }
        })
        if (res && res.code === 1 && res.data && res.data.analysis) {
          this.aiResult = res.data.analysis
        } else {
          this.aiResult = res.msg || this.$t('dashboard.indicator.backtest.historyNoAIResult')
        }
      } finally {
        this.analyzing = false
      }
    }
  }
}
</script>

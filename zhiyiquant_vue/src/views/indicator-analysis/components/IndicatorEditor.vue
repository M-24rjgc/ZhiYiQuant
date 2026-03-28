<template>
  <div>
    <a-modal
      :title="$t('dashboard.indicator.editor.title')"
      :visible="visible"
      :width="isMobile ? '100%' : '95vw'"
      :confirmLoading="saving"
      @ok="handleSave"
      @cancel="handleCancel"
      @afterClose="handleAfterClose"
      :okText="$t('dashboard.indicator.editor.save')"
      :cancelText="$t('dashboard.indicator.editor.cancel')"
      :maskClosable="false"
      :centered="false"
      :style="isMobile ? { top: 0, paddingBottom: 0 } : { top: '2%' }"
      class="indicator-editor-modal"
    >
      <div class="editor-content">
        <a-row :gutter="16" class="editor-layout" :class="{ 'mobile-layout': isMobile }">
          <!-- 宸︿晶锛氫唬鐮佺紪杈戝櫒鍜屾櫤鑳界敓鎴?-->
          <a-col :span="24" :xs="24" :sm="24" :md="24" class="code-editor-column">
            <div class="code-section">
              <div class="section-header">
                <div class="header-left">
                  <span class="section-title">{{ $t('dashboard.indicator.editor.code') }}</span>
                </div>
                <div class="section-actions">
                  <a-button
                    type="link"
                    size="small"
                    @click="handleVerifyCode"
                    :loading="verifying"
                    style="padding: 0 8px; color: #52c41a; font-weight: bold;"
                  >
                    <a-icon type="check-circle" />
                    {{ $t('dashboard.indicator.editor.verifyCode') }}
                  </a-button>
                  <a-button type="link" size="small" @click="goToDocs" style="padding: 0;">
                    <a-icon type="book" />
                    {{ $t('dashboard.indicator.editor.guide') }}
                  </a-button>
                </div>
              </div>

              <a-alert
                type="info"
                show-icon
                style="margin-bottom: 12px;"
                :message="$t('dashboard.indicator.boundary.message')"
                :description="$t('dashboard.indicator.boundary.indicatorRule')"
              />

              <!-- 浠ｇ爜缂栬緫鍣ㄦā寮?-->
              <div class="code-mode-split">
                <a-row :gutter="16" class="code-mode-row">
                  <!-- 宸︼細浠ｇ爜缂栬緫鍣?-->
                  <a-col :xs="24" :sm="24" :md="18" class="code-pane">
                    <div ref="codeEditorContainer" class="code-editor-container"></div>
                  </a-col>
                  <!-- 鍙筹細AI 鐢熸垚 -->
                  <a-col :xs="24" :sm="24" :md="6" class="ai-pane">
                    <div class="ai-panel">
                      <div class="ai-panel-title">
                        <a-icon type="robot" />
                        <span>{{ $t('dashboard.indicator.editor.aiGenerate') }}</span>
                      </div>
                      <a-textarea
                        v-model="aiPrompt"
                        :placeholder="$t('dashboard.indicator.editor.aiPromptPlaceholder')"
                        :rows="12"
                        :auto-size="{ minRows: 12, maxRows: 20 }"
                      />
                      <a-button
                        type="primary"
                        block
                        @click="handleAIGenerate"
                        :loading="aiGenerating"
                        size="large"
                        style="margin-top: 10px;"
                      >
                        {{ $t('dashboard.indicator.editor.aiGenerateBtn') }}
                      </a-button>
                    </div>
                  </a-col>
                </a-row>
              </div>
            </div>
          </a-col>
        </a-row>
      </div>
      <div slot="footer" class="editor-footer">
        <a-button @click="handleCancel">
          {{ $t('dashboard.indicator.editor.cancel') }}
        </a-button>
        <a-button type="primary" @click="handleSave" :loading="saving">
          {{ $t('dashboard.indicator.editor.save') }}
        </a-button>
      </div>
    </a-modal>

  </div>
</template>

<script>
import CodeMirror from 'codemirror'
import 'codemirror/lib/codemirror.css'
// Python 妯″紡
import 'codemirror/mode/python/python'
// 涓婚锛堝彲閫夛級
import 'codemirror/theme/monokai.css'
import 'codemirror/theme/eclipse.css'
// 甯哥敤鎻掍欢
import 'codemirror/addon/edit/closebrackets'
import 'codemirror/addon/edit/matchbrackets'
import 'codemirror/addon/selection/active-line'
import storage from 'store'
import { ACCESS_TOKEN } from '@/store/mutation-types'
import request from '@/utils/request'

export default {
  name: 'IndicatorEditor',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    indicator: {
      type: Object,
      default: null
    },
    userId: {
      type: Number,
      default: null
    }
  },
  data () {
    return {
      saving: false,
      codeEditor: null,
      aiPrompt: '',
      aiGenerating: false,
      verifying: false,
      isMobile: false
    }
  },
  computed: {},
  watch: {
    visible (val) {
      if (val) {
        // Modal 打开时，等待 DOM 更新后初始化编辑器。
        this.$nextTick(() => {
          // 寤惰繜涓€涓嬬‘淇?Modal 瀹屽叏娓叉煋锛岃〃鍗曞瓧娈靛凡娉ㄥ唽
          setTimeout(() => {
            if (!this.codeEditor && this.$refs.codeEditorContainer) {
              this.initCodeEditor()
            }

            // 初始化表单数据。
            this.initFormData()
          }, 200)
        })
      } else {
        // Modal 关闭时刷新编辑器，保证下次打开显示正常。
        if (this.codeEditor) {
          this.codeEditor.refresh()
        }
      }
    },
    indicator: {
      handler (val) {
        if (val && this.visible) {
          // 褰?indicator 鍙樺寲涓斿脊绐楀彲瑙佹椂锛岀瓑寰呬竴涓嬪啀鏇存柊琛ㄥ崟鏁版嵁
          this.$nextTick(() => {
            setTimeout(() => {
              this.initFormData()
            }, 100)
          })
        }
      },
      deep: true
    }
  },
  mounted () {
    // 检测是否为手机端。
    this.checkMobile()
    window.addEventListener('resize', this.checkMobile)

    // 濡傛灉 visible 鍒濆涓?true锛屼篃瑕佸垵濮嬪寲
    if (this.visible) {
      this.$nextTick(() => {
        setTimeout(() => {
          this.initCodeEditor()
        }, 100)
      })
    }
  },
  beforeDestroy () {
    window.removeEventListener('resize', this.checkMobile)
    if (this.codeEditor) {
      try {
        // fromTextArea() instances have toTextArea(); CodeMirror(div, ...) does not.
        if (typeof this.codeEditor.toTextArea === 'function') {
          this.codeEditor.toTextArea()
        } else if (typeof this.codeEditor.getWrapperElement === 'function') {
          const wrapper = this.codeEditor.getWrapperElement()
          if (wrapper && wrapper.parentNode) {
            wrapper.parentNode.removeChild(wrapper)
          }
        }
      } catch (e) {
        // ignore destroy errors
      } finally {
        this.codeEditor = null
      }
    }
  },
  methods: {
    // Default indicator template (buy/sell only). Shown when creating a new indicator.
    // NOTE: Keep comments and default texts in English (project convention).
    getDefaultIndicatorCode () {
      return `#Demo Code:
#my_indicator_name = "My Buy/Sell Indicator"
#my_indicator_description = "Buy/Sell only; execution is normalized in backend."

#df = df.copy()
#sma = df["close"].rolling(14).mean()
#buy = (df["close"] > sma) & (df["close"].shift(1) <= sma.shift(1))
#sell = (df["close"] < sma) & (df["close"].shift(1) >= sma.shift(1))
#df["buy"] = buy.fillna(False).astype(bool)
#df["sell"] = sell.fillna(False).astype(bool)

#buy_marks = [df["low"].iloc[i] * 0.995 if df["buy"].iloc[i] else None for i in range(len(df))]
#sell_marks = [df["high"].iloc[i] * 1.005 if df["sell"].iloc[i] else None for i in range(len(df))]

#output = {
#  "name": my_indicator_name,
#  "plots": [],
#  "signals": [
#    {"type": "buy", "text": "B", "data": buy_marks, "color": "#00E676"},
#    {"type": "sell", "text": "S", "data": sell_marks, "color": "#FF5252"}
#  ]
#}
`
    },
    // 检测是否为手机端。
    checkMobile () {
      this.isMobile = window.innerWidth <= 768
    },

    /* Visual editor removed (code mode only).

      // Helper function for crossovers
      code += `def crossover(series1, series2):\n`
      code += `    return (series1 > series2) & (series1.shift(1) <= series2.shift(1))\n\n`
      code += `def crossunder(series1, series2):\n`
      code += `    return (series1 < series2) & (series1.shift(1) >= series2.shift(1))\n\n`

      modules.forEach((mod, idx) => {
        const id = mod.id || (idx + 1)
        const s = mod.style

        if (mod.type === 'SMA') {
          code += `# Module ${id}: SMA\n`
          code += `sma_${id} = df['${mod.params.source}'].rolling(${mod.params.period}).mean()\n`
          code += `output_plots.append({ "name": "SMA ${mod.params.period} (#${id})", "data": sma_${id}.tolist(), "color": "${s.color}", "overlay": ${s.overlay ? 'True' : 'False'} })\n\n`
        } else if (mod.type === 'EMA') {
          code += `# Module ${id}: EMA\n`
          code += `ema_${id} = df['${mod.params.source}'].ewm(span=${mod.params.period}, adjust=False).mean()\n`
          code += `output_plots.append({ "name": "EMA ${mod.params.period} (#${id})", "data": ema_${id}.tolist(), "color": "${s.color}", "overlay": ${s.overlay ? 'True' : 'False'} })\n\n`
        } else if (mod.type === 'RSI') {
          code += `# Module ${id}: RSI\n`
          code += `delta_${id} = df['close'].diff()\n`
          code += `gain_${id} = (delta_${id}.where(delta_${id} > 0, 0)).ewm(alpha=1/${mod.params.period}, adjust=False).mean()\n`
          code += `loss_${id} = (-delta_${id}.where(delta_${id} < 0, 0)).ewm(alpha=1/${mod.params.period}, adjust=False).mean()\n`
          code += `rs_${id} = gain_${id} / loss_${id}\n`
          code += `rsi_${id} = 100 - (100 / (1 + rs_${id}))\n`
          code += `output_plots.append({ "name": "RSI ${mod.params.period} (#${id})", "data": rsi_${id}.tolist(), "color": "${s.color}", "overlay": False })\n`
          code += `output_plots.append({ "name": "Overbought", "data": [70]*len(df), "color": "#999", "style": "dashed", "overlay": False })\n`
          code += `output_plots.append({ "name": "Oversold", "data": [30]*len(df), "color": "#999", "style": "dashed", "overlay": False })\n\n`
        } else if (mod.type === 'MACD') {
            code += `# Module ${id}: MACD\n`
            code += `exp1_${id} = df['close'].ewm(span=${mod.params.fast}, adjust=False).mean()\n`
            code += `exp2_${id} = df['close'].ewm(span=${mod.params.slow}, adjust=False).mean()\n`
            code += `macd_${id} = exp1_${id} - exp2_${id}\n`
            code += `signal_${id} = macd_${id}.ewm(span=${mod.params.signal}, adjust=False).mean()\n`
            code += `hist_${id} = macd_${id} - signal_${id}\n`
            code += `output_plots.append({ "name": "MACD (#${id})", "data": macd_${id}.tolist(), "color": "${s.color}", "overlay": False })\n`
            code += `output_plots.append({ "name": "Signal (#${id})", "data": signal_${id}.tolist(), "color": "#ff9f43", "overlay": False })\n`
            code += `output_plots.append({ "name": "Hist (#${id})", "data": hist_${id}.tolist(), "color": "#ccc", "type": "bar", "overlay": False })\n\n`
        } else if (mod.type === 'BOLL') {
            code += `# Module ${id}: BOLL\n`
            code += `mid_${id} = df['close'].rolling(${mod.params.period}).mean()\n`
            code += `std_${id} = df['close'].rolling(${mod.params.period}).std()\n`
            code += `upper_${id} = mid_${id} + (${mod.params.std} * std_${id})\n`
            code += `lower_${id} = mid_${id} - (${mod.params.std} * std_${id})\n`
            code += `output_plots.append({ "name": "Boll Upper (#${id})", "data": upper_${id}.tolist(), "color": "${s.color}", "overlay": True })\n`
            code += `output_plots.append({ "name": "Boll Lower (#${id})", "data": lower_${id}.tolist(), "color": "${s.color}", "overlay": True })\n`
            code += `output_plots.append({ "name": "Boll Mid (#${id})", "data": mid_${id}.tolist(), "color": "${s.color}", "style": "dashed", "overlay": True })\n\n`
        } else if (mod.type === 'KDJ') {
            code += `# Module ${id}: KDJ\n`
            code += `low_min_${id} = df['low'].rolling(${mod.params.period}).min()\n`
            code += `high_max_${id} = df['high'].rolling(${mod.params.period}).max()\n`
            code += `rsv_${id} = (df['close'] - low_min_${id}) / (high_max_${id} - low_min_${id}) * 100\n`
            code += `k_${id} = rsv_${id}.ewm(alpha=1/${mod.params.m1}, adjust=False).mean()\n`
            code += `d_${id} = k_${id}.ewm(alpha=1/${mod.params.m2}, adjust=False).mean()\n`
            code += `j_${id} = 3 * k_${id} - 2 * d_${id}\n`
            code += `output_plots.append({ "name": "K (#${id})", "data": k_${id}.tolist(), "color": "${s.color}", "overlay": False })\n`
            code += `output_plots.append({ "name": "D (#${id})", "data": d_${id}.tolist(), "color": "#ff9f43", "overlay": False })\n`
            code += `output_plots.append({ "name": "J (#${id})", "data": j_${id}.tolist(), "color": "#ffec3d", "overlay": False })\n\n`
        } else if (mod.type === 'CCI') {
            code += `# Module ${id}: CCI\n`
            code += `tp_${id} = (df['high'] + df['low'] + df['close']) / 3\n`
            code += `ma_${id} = tp_${id}.rolling(${mod.params.period}).mean()\n`
            code += `md_${id} = tp_${id}.rolling(${mod.params.period}).apply(lambda x: np.mean(np.abs(x - np.mean(x))))\n`
            code += `cci_${id} = (tp_${id} - ma_${id}) / (0.015 * md_${id})\n`
            code += `output_plots.append({ "name": "CCI (#${id})", "data": cci_${id}.tolist(), "color": "${s.color}", "overlay": False })\n`
            code += `output_plots.append({ "name": "Upper", "data": [100]*len(df), "color": "#999", "style": "dashed", "overlay": False })\n`
            code += `output_plots.append({ "name": "Lower", "data": [-100]*len(df), "color": "#999", "style": "dashed", "overlay": False })\n\n`
        } else if (mod.type === 'ATR') {
            code += `# Module ${id}: ATR\n`
            code += `tr1_${id} = df['high'] - df['low']\n`
            code += `tr2_${id} = (df['high'] - df['close'].shift(1)).abs()\n`
            code += `tr3_${id} = (df['low'] - df['close'].shift(1)).abs()\n`
            code += `tr_${id} = pd.concat([tr1_${id}, tr2_${id}, tr3_${id}], axis=1).max(axis=1)\n`
            code += `atr_${id} = tr_${id}.rolling(${mod.params.period}).mean()\n`
            code += `output_plots.append({ "name": "ATR (#${id})", "data": atr_${id}.tolist(), "color": "${s.color}", "overlay": False })\n\n`
        } else if (mod.type === 'SIGNAL') {
            code += `# Module ${id}: Signal Logic\n`

            // Helper to get variable name or default to 'close' if not found or 'close'
            const getVar = (val) => {
                if (!val || val === 'close') return "df['close']"
                // Check if it's a numeric constant
                if (!isNaN(parseFloat(val))) return parseFloat(val)
                return val
            }

            const leftBuy = getVar(mod.params.buy_cond_left)
            const rightBuy = getVar(mod.params.buy_cond_right)
            let buyCond = ''

            if (mod.params.buy_op === '>') buyCond = `(${leftBuy} > ${rightBuy})`
            else if (mod.params.buy_op === '<') buyCond = `(${leftBuy} < ${rightBuy})`
            else if (mod.params.buy_op === 'cross_up') buyCond = `crossover(${leftBuy}, ${rightBuy})`
            else if (mod.params.buy_op === 'cross_down') buyCond = `crossunder(${leftBuy}, ${rightBuy})`

            const leftSell = getVar(mod.params.sell_cond_left)
            const rightSell = getVar(mod.params.sell_cond_right)
            let sellCond = ''

            if (mod.params.sell_op === '>') sellCond = `(${leftSell} > ${rightSell})`
            else if (mod.params.sell_op === '<') sellCond = `(${leftSell} < ${rightSell})`
            else if (mod.params.sell_op === 'cross_up') sellCond = `crossover(${leftSell}, ${rightSell})`
            else if (mod.params.sell_op === 'cross_down') sellCond = `crossunder(${leftSell}, ${rightSell})`

            code += `buy_signal_${id} = ${buyCond}\n`
            code += `sell_signal_${id} = ${sellCond}\n`

            code += `output_signals.append({\n`
            code += `    "type": "buy",\n`
            code += `    "text": "B",\n`
            code += `    "data": [df['low'].iloc[i] * 0.995 if buy_signal_${id}.iloc[i] else None for i in range(len(df))],\n`
            code += `    "color": "#00E676"\n`
            code += `})\n`
            code += `output_signals.append({\n`
            code += `    "type": "sell",\n`
            code += `    "text": "S",\n`
            code += `    "data": [df['high'].iloc[i] * 1.005 if sell_signal_${id}.iloc[i] else None for i in range(len(df))],\n`
            code += `    "color": "#FF5252"\n`
            code += `})\n\n`
        }
      })

      code += `output = {\n`
      code += `    "name": my_indicator_name,\n`
      code += `    "plots": output_plots,\n`
      code += `    "signals": output_signals\n`
      code += `}\n`

      this.codeEditor.setValue(code)
      this.editMode = 'code'
      this.$message.success('浠ｇ爜鐢熸垚鎴愬姛锛?)
    },
    parseConfigFromCode (code) {
      if (!code) return
      const regex = /# <VISUAL_CONF>\s*\n# (.*?)\s*\n# <\/VISUAL_CONF>/s
      const match = code.match(regex)
      if (match && match[1]) {
        try {
          this.visualModules = JSON.parse(match[1])
          this.editMode = 'visual' // Auto-switch to visual if config found
        } catch (e) {
          console.error('Failed to parse visual config', e)
        }
      } else {
        this.editMode = 'code'
        this.visualModules = []
      }
    },

    */

    // 打开策略开发指南说明。
    goToDocs () {
      this.$info({
        title: '策略开发指南',
        content: '请查看本地仓库中的 docs/STRATEGY_DEV_GUIDE_CN.md。'
      })
    },

    // 楠岃瘉浠ｇ爜
    handleVerifyCode () {
      const code = this.codeEditor ? this.codeEditor.getValue() : ''
      if (!code || !code.trim()) {
        this.$message.warning(this.$t('dashboard.indicator.editor.verifyCodeEmpty'))
        return
      }

      this.verifying = true
      // 浣跨敤 request 宸ュ叿锛坅xios锛夊彂閫佽姹傦紝瀹冧細鑷姩澶勭悊 baseURL 鍜?token
      request({
        url: '/api/indicator/verifyCode',
        method: 'post',
        data: { code: code }
      }).then(res => {
        if (res.code === 1) {
          const data = res.data || {}
          this.$message.success(`${this.$t('dashboard.indicator.editor.verifyCodeSuccess')} (${data.plots_count || 0} plots, ${data.signals_count || 0} signals)`)
        } else {
          // 鏄剧ず璇︾粏閿欒
          const errorData = res.data || {}
          this.$error({
            title: this.$t('dashboard.indicator.editor.verifyCodeFailed'),
            width: 600,
            content: (h) => {
              return h('div', [
                h('p', { style: { fontWeight: 'bold', color: '#ff4d4f' } }, res.msg),
                errorData.details ? h('pre', {
                  style: {
                    background: '#f5f5f5',
                    padding: '8px',
                    overflow: 'auto',
                    maxHeight: '300px',
                    marginTop: '8px',
                    fontSize: '12px',
                    fontFamily: 'monospace'
                  }
                }, errorData.details) : null
              ])
            }
          })
        }
      }).catch(err => {
        this.$message.error('Request Failed: ' + (err.message || 'Unknown Error'))
      }).finally(() => {
        this.verifying = false
      })
    },

    // 清理代码中的 markdown 代码块标记。
    cleanMarkdownCodeBlocks (code) {
      if (!code || typeof code !== 'string') {
        return code
      }

      let cleanedCode = code.trim()

      // 妫€鏌ユ槸鍚﹀寘鍚唬鐮佸潡鏍囪
      const hasCodeBlockMarkers = /```/.test(cleanedCode)

      if (!hasCodeBlockMarkers) {
        // 濡傛灉娌℃湁浠ｇ爜鍧楁爣璁帮紝鐩存帴杩斿洖
        return cleanedCode
      }

      // 绉婚櫎寮€澶寸殑浠ｇ爜鍧楁爣璁帮紙濡?```python銆乣``py銆乣`` 绛夛級
      cleanedCode = cleanedCode.replace(/^```[\w]*\s*\n?/i, '')

      // 濡傛灉杩樻湁寮€澶存爣璁帮紙鍙兘娌℃湁璇█鏍囪瘑锛夛紝鍐嶆灏濊瘯绉婚櫎
      if (cleanedCode.startsWith('```')) {
        cleanedCode = cleanedCode.replace(/^```\s*\n?/g, '')
      }

      if (cleanedCode.endsWith('```')) {
        cleanedCode = cleanedCode.replace(/\n?```\s*$/g, '')
      }

      // 绉婚櫎浠ｇ爜鍧椾腑闂村彲鑳藉嚭鐜扮殑 ```鏍囪锛堥€氬父鏄敊璇爣璁帮級
      cleanedCode = cleanedCode.replace(/^\s*```[\w]*\s*$/gm, '')
      cleanedCode = cleanedCode.replace(/^\s*```\s*$/gm, '')

      cleanedCode = cleanedCode.replace(/\n{3,}/g, '\n\n')

      // 鍐嶆娓呯悊棣栧熬绌虹櫧
      cleanedCode = cleanedCode.trim()

      return cleanedCode
    },
    // 初始化弹窗数据（编辑/新建）。
    initFormData () {
      if (!this.visible) {
        return
      }

      let code = this.indicator ? (this.indicator.code || '') : ''
      // If creating a new indicator (or code is empty), show the default template.
      if (!code || !String(code).trim()) {
        code = this.getDefaultIndicatorCode()
      }
      this.$nextTick(() => {
        setTimeout(() => {
          this.aiPrompt = ''
          if (this.codeEditor) {
            this.codeEditor.setValue(code)
            this.codeEditor.refresh()
          }
          // Visual editor removed
        }, 50)
      })
    },
    initCodeEditor () {
      if (!this.$refs.codeEditorContainer) {
        return
      }

      if (this.codeEditor) {
        try {
          if (typeof this.codeEditor.toTextArea === 'function') {
            this.codeEditor.toTextArea()
          } else if (typeof this.codeEditor.getWrapperElement === 'function') {
            const wrapper = this.codeEditor.getWrapperElement()
            if (wrapper && wrapper.parentNode) {
              wrapper.parentNode.removeChild(wrapper)
            }
          }
        } catch (e) {
        }
        this.codeEditor = null
      }

      try {
        // 娓呯┖瀹瑰櫒
        this.$refs.codeEditorContainer.innerHTML = ''

        this.codeEditor = CodeMirror(this.$refs.codeEditorContainer, {
          value: (() => {
            const existing = this.indicator ? (this.indicator.code || '') : ''
            return existing && String(existing).trim() ? existing : this.getDefaultIndicatorCode()
          })(),
          mode: 'python',
          theme: 'eclipse',
          lineNumbers: true,
          lineWrapping: true,
          indentUnit: 4,
          indentWithTabs: false,
          smartIndent: true,
          matchBrackets: true,
          autoCloseBrackets: true,
          styleActiveLine: true,
          foldGutter: false,
          gutters: ['CodeMirror-linenumbers'],
          tabSize: 4,
          viewportMargin: Infinity
        })

        // 鐩戝惉浠ｇ爜鍙樺寲锛屽悓姝ュ埌琛ㄥ崟
        this.codeEditor.on('change', (editor) => {
          // no-op: form fields removed; code is read from editor on save
          editor.getValue()
        })

        // 鍒锋柊缂栬緫鍣ㄤ互纭繚姝ｇ‘鏄剧ず
        this.$nextTick(() => {
          if (this.codeEditor) {
            this.codeEditor.refresh()
          }
        })
      } catch (error) {
      }
    },
    handleSave () {
      const code = this.codeEditor ? this.codeEditor.getValue() : ''
      const finalCode = code || ''
      if (!finalCode.trim()) {
        this.$message.warning(this.$t('dashboard.indicator.editor.codeRequired'))
        return
      }

      this.saving = true
      // 瑙﹀彂淇濆瓨浜嬩欢锛歯ame/description 绛夊瓧娈靛凡绉婚櫎锛屽悗绔細浠庝唬鐮佷腑瑙ｆ瀽
      this.$emit('save', {
        id: this.indicator ? this.indicator.id : 0,
        code: finalCode,
        userid: this.userId
      })
    },
    handleCancel () {
      if (this.codeEditor) {
        this.codeEditor.setValue('')
      }
      this.$emit('cancel')
    },
    handleAfterClose () {
      if (this.codeEditor) {
        this.$nextTick(() => {
          if (this.codeEditor) {
            this.codeEditor.refresh()
          }
        })
      }

      this.aiPrompt = ''
    },
    async handleAIGenerate () {
      if (!this.aiPrompt || !this.aiPrompt.trim()) {
        this.$message.warning(this.$t('dashboard.indicator.editor.aiPromptRequired'))
        return
      }

      this.aiGenerating = true

      // 鑾峰彇缂栬緫鍣ㄤ腑鐨勭幇鏈変唬鐮佷綔涓轰笂涓嬫枃
      let existingCode = ''
      if (this.codeEditor) {
        existingCode = this.codeEditor.getValue() || ''
      }

      if (this.codeEditor) {
        this.codeEditor.setValue('# AI generating...\n')
        this.codeEditor.refresh()
      }

      let generatedCode = ''

      try {
        // Local python API (SSE)
        const url = '/api/indicator/aiGenerate'

        // 鑾峰彇 token
        const token = storage.get(ACCESS_TOKEN)

        const requestBody = {
          prompt: this.aiPrompt.trim()
        }

        if (existingCode.trim()) {
          requestBody.existingCode = existingCode.trim()
        }

        // 浣跨敤 fetch 澶勭悊娴佸紡鍝嶅簲
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : '',
            'Access-Token': token || '',
            'Token': token || ''
          },
          body: JSON.stringify(requestBody),
          credentials: 'include'
        })

        if (!response.ok) {
          const text = await response.text().catch(() => '')
          throw new Error(text || `HTTP error! status: ${response.status}`)
        }

        // 澶勭悊娴佸紡鍝嶅簲
        if (!response.body || typeof response.body.getReader !== 'function') {
          throw new Error('AI 鏈嶅姟鏈繑鍥炲彲璇诲彇鐨勬祦锛坮esponse.body 涓嶅瓨鍦級')
        }
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()

          if (done) {
            break
          }

          buffer += decoder.decode(value, { stream: true })

          // 澶勭悊瀹屾暣鐨?SSE 娑堟伅
          const lines = buffer.split('\n\n')
          buffer = lines.pop() || '' // 淇濈暀鏈€鍚庝竴涓笉瀹屾暣鐨勬秷鎭?
          for (const line of lines) {
            if (!line.trim() || !line.startsWith('data: ')) {
              continue
            }

            const data = line.substring(6) // 绉婚櫎 "data: " 鍓嶇紑

            if (data === '[DONE]') {
              // 娴佸紡浼犺緭瀹屾垚
              break
            }

            try {
              const json = JSON.parse(data)

              if (json.error) {
                throw new Error(json.error)
              }

              if (json.content) {
                generatedCode += json.content

                const cleanedCode = this.cleanMarkdownCodeBlocks(generatedCode)

                if (this.codeEditor) {
                  this.codeEditor.setValue(cleanedCode)
                  const lineCount = this.codeEditor.lineCount()
                  this.codeEditor.setCursor({ line: lineCount - 1, ch: 0 })
                  this.codeEditor.refresh()
                }
              }
            } catch (parseError) {
            }
          }
        }

        if (this.codeEditor && generatedCode) {
          const cleanedCode = this.cleanMarkdownCodeBlocks(generatedCode)
          this.codeEditor.setValue(cleanedCode)
          this.codeEditor.refresh()
          this.$message.success(this.$t('dashboard.indicator.editor.aiGenerateSuccess'))
        } else if (!generatedCode) {
          this.$message.warning('鏈敓鎴愪换浣曚唬鐮侊紝璇峰皾璇曟洿璇︾粏鐨勬彁绀鸿瘝')
        }
      } catch (error) {
        this.$message.error(error.message || this.$t('dashboard.indicator.editor.aiGenerateError'))

        if (generatedCode && this.codeEditor) {
          const cleanedCode = this.cleanMarkdownCodeBlocks(generatedCode)
          this.codeEditor.setValue(cleanedCode)
        }
      } finally {
        this.aiGenerating = false
      }
    }
    // 鍙戝竷鍒扮ぞ鍖?/ 瀹氫环 / 棰勮鍥句笂浼?绛夊姛鑳藉凡绉婚櫎锛堝紑婧愭湰鍦扮増涓嶉渶瑕侊級
  }
}
</script>

<style lang="less" scoped>
:deep(.ant-modal) {
      top: 20px !important;
    }
.visual-editor-container {
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  height: 500px; /* Increased height */
  overflow: hidden;
}

.visual-modules-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.empty-visual-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
}

.visual-module-card {
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  margin-bottom: 12px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);

  .module-header {
    padding: 8px 12px;
    border-bottom: 1px solid #f0f0f0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #f9f9f9;

    .module-title {
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .remove-icon {
      cursor: pointer;
      color: #999;
      &:hover { color: #ff4d4f; }
    }
  }

  .module-body {
    padding: 12px;
  }

  .style-config {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px dashed #f0f0f0;

    .label {
      margin-right: 8px;
      color: #666;
    }
  }
}

.add-module-bar {
  padding: 12px;
  background: #fff;
  border-top: 1px solid #e8e8e8;
}

/* 鎵嬫満绔€傞厤 */
@media (max-width: 768px) {
  .visual-editor-container {
      height: auto;
      min-height: 400px;
  }
}

.ant-form-item {
  margin-bottom: 16px;
}

.editor-content {
  padding: 24px;
  background: #fff;
  min-height: 500px;
  max-height: 82vh;
  overflow-y: auto;
}

.editor-layout {
  min-height: 450px;
}

.code-editor-column {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.code-section {
  display: flex;
  flex-direction: column;
  flex: 0 0 auto;
  margin-bottom: 16px;

  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
    padding-bottom: 12px;
    border-bottom: 2px solid #f0f0f0;

    .section-title {
      font-weight: 600;
      font-size: 14px;
      color: #262626;
      display: flex;
      align-items: center;
      gap: 8px;

      &::before {
        content: '';
        display: inline-block;
        width: 4px;
        height: 14px;
        background: #1890ff;
        border-radius: 2px;
      }
    }

    .section-actions {
      display: flex;
      align-items: center;
      gap: 8px;

      :deep(.ant-btn-link) {
        color: #1890ff;
        padding: 0 8px;

        &:hover {
          color: #40a9ff;
        }
      }
    }
  }
}

.code-editor-container {
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  overflow: hidden;
  height: 62vh;
  min-height: 520px;
  max-height: none;
  display: flex;
  flex-direction: column;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;

  &:hover {
    border-color: #40a9ff;
  }

  &:focus-within {
    border-color: #1890ff;
    box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2), inset 0 1px 3px rgba(0, 0, 0, 0.05);
  }

  :deep(.CodeMirror) {
    flex: 1;
    height: 100%;
    font-family: 'Courier New', Consolas, 'Liberation Mono', Menlo, monospace;
    font-size: 13px;
    line-height: 1.6;
    display: flex;
    flex-direction: column;
    background: #fafafa;
  }

  :deep(.CodeMirror-scroll) {
    flex: 1;
    min-height: 100%;
    max-height: none;
    overflow-y: auto;
    overflow-x: auto;
  }

  :deep(.CodeMirror-sizer) {
    min-height: 100% !important;
    padding-left: 12px !important;
  }

  :deep(.CodeMirror-gutters) {
    border-right: 1px solid #e8e8e8;
    background: linear-gradient(to right, #fafafa 0%, #f5f5f5 100%);
    width: 45px;
    padding-right: 4px;
  }

  :deep(.CodeMirror-linenumber) {
    padding: 0 8px 0 4px;
    min-width: 30px;
    text-align: right;
    color: #999;
    font-size: 12px;
  }

  :deep(.CodeMirror-lines) {
    padding: 12px 8px;
    background: #fff;
  }

  :deep(.CodeMirror-line) {
    padding-left: 0;
  }

  :deep(.CodeMirror-cursor) {
    border-left: 2px solid #1890ff;
  }

  :deep(.CodeMirror-selected) {
    background: #e6f7ff;
  }
}

.code-mode-split {
  width: 100%;
}

.ai-pane {
  display: flex;
  flex-direction: column;
}

.ai-panel {
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  background: #fafafa;
  padding: 12px;
  height: 62vh;
  min-height: 520px;
  display: flex;
  flex-direction: column;
}

.ai-panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  margin-bottom: 10px;
  color: #262626;
}

.ai-panel-hint {
  margin-top: 10px;
  color: #8c8c8c;
  font-size: 12px;
  line-height: 1.5;
}

.ai-panel :deep(textarea.ant-input) {
  flex: 1;
  resize: none;
}

.editor-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;

  :deep(.ant-btn) {
    height: 36px;
    padding: 0 20px;
    font-weight: 500;
    border-radius: 4px;
    transition: all 0.3s ease;

    &:not(.ant-btn-primary) {
      &:hover {
        border-color: #40a9ff;
        color: #40a9ff;
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(24, 144, 255, 0.2);
      }
    }

    &.ant-btn-primary {
      box-shadow: 0 2px 4px rgba(24, 144, 255, 0.3);

      &:hover {
        box-shadow: 0 4px 12px rgba(24, 144, 255, 0.4);
        transform: translateY(-1px);
      }
    }
  }
}

/* 鎵嬫満绔€傞厤 */
@media (max-width: 768px) {
  .indicator-editor-modal {
    :deep(.ant-modal) {
      width: 100% !important;
      max-width: 100% !important;
      margin: 0 !important;
      top: 0 !important;
      padding-bottom: 0 !important;
      max-height: 100vh !important;
    }

    :deep(.ant-modal-content) {
      height: 100vh !important;
      max-height: 100vh !important;
      display: flex;
      flex-direction: column;
      border-radius: 0 !important;
    }

    :deep(.ant-modal-header) {
      flex-shrink: 0;
      padding: 16px;
      border-bottom: 1px solid #e8e8e8;
    }

    :deep(.ant-modal-body) {
      flex: 1;
      overflow-y: auto;
      padding: 0 !important;
      min-height: 0;
    }

    :deep(.ant-modal-footer) {
      flex-shrink: 0;
      padding: 12px 16px;
      border-top: 1px solid #e8e8e8;
    }
  }

  .editor-content {
    padding: 16px !important;
    min-height: auto !important;
    max-height: none !important;
    overflow-y: visible !important;
  }

  .editor-layout {
    min-height: auto !important;
  }

  /* 宸﹀彸甯冨眬鏀逛负涓婁笅甯冨眬 */
  .code-editor-column {
    width: 100% !important;
    margin-bottom: 16px;
  }

  /* 浠ｇ爜缂栬緫鍣ㄥ尯鍩?*/
  .code-section {
    margin-bottom: 16px;

    .section-header {
      padding-bottom: 8px;
      margin-bottom: 8px;

      .section-title {
        font-size: 13px;
      }
    }
  }

  .code-editor-container {
    height: 250px !important;
    min-height: 250px !important;
    max-height: 250px !important;

    :deep(.CodeMirror-scroll) {
      min-height: 250px !important;
      max-height: 250px !important;
    }

    :deep(.CodeMirror-sizer) {
      min-height: 250px !important;
    }
  }

  /* 鏅鸿兘鐢熸垚鍖哄煙 */
  .ai-panel {
    height: auto !important;
    min-height: auto !important;
  }

  /* 搴曢儴鎸夐挳 */
  .editor-footer {
    flex-direction: column-reverse;
    gap: 8px;
    padding: 0;

    :deep(.ant-btn) {
      width: 100%;
      height: 40px;
      margin: 0;
    }
  }
}
</style>

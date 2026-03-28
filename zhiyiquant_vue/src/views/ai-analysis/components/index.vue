<template>
  <div class="metaverse-container" :style="cssVars">
    <!-- 背景特效 -->
    <div class="bg-grid"></div>
    <div class="bg-glow"></div>
    <div class="bg-particles">
      <div v-for="n in 20" :key="n" class="particle" :style="getParticleStyle(n)"></div>
    </div>

    <!-- 主控台区域 -->
    <div class="main-console" :class="{ 'has-result': hasResult || hasAnalysisResults }">

      <!-- 左侧：Agent 团队状态 -->
      <div class="left-panel">
        <div class="agents-panel custom-scroll">
          <div class="panel-title">{{ $t('ai-analysis.panel.roster') }}</div>
          <div class="agents-list" ref="agentsList">
            <div
              v-for="(agent, index) in reversedAgents"
              :key="index"
              class="agent-card"
              :class="{
                'active': getAgentStatus(agents.length - 1 - index) === 'active',
                'completed': getAgentStatus(agents.length - 1 - index) === 'completed',
                'waiting': getAgentStatus(agents.length - 1 - index) === 'waiting',
                'selected': (hasResult || hasAnalysisResults) && selectedAgentIndex === (agents.length - 1 - index)
              }"
              :id="'agent-' + (agents.length - 1 - index)"
              @click="handleAgentClick(agents.length - 1 - index)"
              :style="{ cursor: (hasResult || hasAnalysisResults) ? 'pointer' : 'default' }"
            >
              <div class="agent-avatar">
                <img :src="`https://api.dicebear.com/9.x/avataaars/svg?seed=${agent.name}&backgroundColor=b6e3f4,c0aede,d1d4f9,ffd5dc,ffdfbf&accessories=prescription01,prescription02&accessoriesColor=262e33,65c9ff,a7ffc4,e6e6e6,ffdeb5,ffffb1&clothing=blazerAndSweater,blazerAndShirt,collarAndSweater,graphicShirt,hoodie&clothingGraphic=bear,cumbia,deer,diamond,hola,pizza,resist&eyebrows=defaultNatural,raisedExcited,sadConcernedNatural&eyes=squint&facialHair[]&hairColor=2c1b18,4a312c,724133,a55728,b58143,c93305,d6b370,ecdcbf,e8e1e1,f59797&mouth=smile,twinkle&top=bigHair,curvy,miaWallace,shortWaved,straightAndStrand,longButNotTooLong,shaggy,shaggyMullet,shortCurly,straight01`" alt="avatar" />
                <div class="pulse-ring" v-if="getAgentStatus(agents.length - 1 - index) === 'active'"></div>
              </div>
              <div class="agent-info">
                <div class="agent-name">{{ $t(agent.nameKey) }}</div>
                <div class="agent-role">{{ $t(agent.roleKey) }}</div>
                <div class="agent-status">
                  <span v-if="getAgentStatus(agents.length - 1 - index) === 'active'" class="typing">{{ $t('ai-analysis.panel.thinking') }}</span>
                  <span v-else-if="getAgentStatus(agents.length - 1 - index) === 'completed'" class="done">{{ $t('ai-analysis.panel.done') }}</span>
                  <span v-else class="wait">{{ $t('ai-analysis.panel.standby') }}</span>
                </div>
              </div>
              <div class="agent-visual" v-if="getAgentStatus(agents.length - 1 - index) === 'active'">
                <a-icon type="loading" spin :style="{ color: 'var(--primary-color)' }" />
              </div>
              <div class="agent-visual" v-if="getAgentStatus(agents.length - 1 - index) === 'completed'">
                <a-icon type="check-circle" theme="filled" style="color: #52c41a" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 中间：结果展示区（任务完成后显示或查看历史记录时） -->
      <div class="middle-panel" v-if="(hasResult || hasAnalysisResults) && analysisResults">
        <div class="result-content custom-scroll">
          <!-- 根据选中的 agent 显示对应的结果 -->
          <div v-if="selectedAgentIndex !== null && getAgentResult(selectedAgentIndex)" class="agent-result-panel">
            <!-- Overview -->
            <div v-if="agents[selectedAgentIndex].resultKey === 'overview' && analysisResults.overview" class="analysis-panel">
              <div class="overview-content">
                <!-- 综合评分卡片 -->
                <div class="score-cards">
                  <a-card class="score-card" :class="getScoreClass(analysisResults.overview?.overallScore)">
                    <div class="score-content">
                      <div class="score-value">{{ analysisResults.overview?.overallScore || '--' }}</div>
                      <div class="score-label">{{ $t('dashboard.analysis.score.overall') }}</div>
                    </div>
                  </a-card>
                  <a-card class="score-card">
                    <div class="score-content">
                      <div class="score-value">{{ analysisResults.overview?.recommendation || '--' }}</div>
                      <div class="score-label">{{ $t('dashboard.analysis.score.recommendation') }}</div>
                    </div>
                  </a-card>
                  <a-card class="score-card">
                    <div class="score-content">
                      <div class="score-value">{{ analysisResults.overview?.confidence || '--' }}%</div>
                      <div class="score-label">{{ $t('dashboard.analysis.score.confidence') }}</div>
                    </div>
                  </a-card>
                </div>
                <!-- 维度评分 -->
                <a-card :title="$t('dashboard.analysis.card.dimensionScores')" style="margin-top: 16px;">
                  <div class="dimension-scores">
                    <div v-for="(score, dimension) in analysisResults.overview?.dimensionScores" :key="dimension" class="dimension-score-item">
                      <div class="dimension-name">{{ getDimensionName(dimension) }}</div>
                      <a-progress :percent="score" :status="getScoreStatus(score)" />
                    </div>
                  </div>
                </a-card>
                <!-- 综合分析报告 -->
                <a-card :title="$t('dashboard.analysis.card.overviewReport')" style="margin-top: 16px;" v-if="analysisResults.overview?.report">
                  <div class="analysis-report" v-html="formatReport(analysisResults.overview.report)"></div>
                </a-card>
              </div>
            </div>

            <!-- Fundamental -->
            <div v-else-if="agents[selectedAgentIndex].resultKey === 'fundamental' && analysisResults.fundamental" class="analysis-panel">
              <div class="fundamental-content">
                <a-card :title="$t('dashboard.analysis.card.financialMetrics')" v-if="analysisResults.fundamental?.financials">
                  <div class="financial-metrics">
                    <div v-for="(value, key) in analysisResults.fundamental.financials" :key="key" class="metric-item">
                      <div class="metric-label">{{ key }}</div>
                      <div class="metric-value">{{ value }}</div>
                    </div>
                  </div>
                </a-card>
                <a-card :title="$t('dashboard.analysis.card.fundamentalReport')" style="margin-top: 16px;" v-if="analysisResults.fundamental?.report">
                  <div class="analysis-report" v-html="formatReport(analysisResults.fundamental.report)"></div>
                </a-card>
              </div>
            </div>

            <!-- Technical -->
            <div v-else-if="agents[selectedAgentIndex].resultKey === 'technical' && analysisResults.technical" class="analysis-panel">
              <div class="technical-content">
                <a-card :title="$t('dashboard.analysis.card.technicalIndicators')" v-if="analysisResults.technical?.indicators">
                  <div class="technical-indicators">
                    <div v-for="(value, key) in analysisResults.technical.indicators" :key="key" class="indicator-item">
                      <div class="indicator-label">{{ key }}</div>
                      <div class="indicator-value" :class="getIndicatorClass(value)">
                        {{ value }}
                      </div>
                    </div>
                  </div>
                </a-card>
                <a-card :title="$t('dashboard.analysis.card.technicalReport')" style="margin-top: 16px;" v-if="analysisResults.technical?.report">
                  <div class="analysis-report" v-html="formatReport(analysisResults.technical.report)"></div>
                </a-card>
              </div>
            </div>

            <!-- News -->
            <div v-else-if="agents[selectedAgentIndex].resultKey === 'news' && analysisResults.news" class="analysis-panel">
              <div class="news-content">
                <a-card :title="$t('dashboard.analysis.card.newsList')" v-if="analysisResults.news?.articles">
                  <div class="news-list">
                    <div v-for="(article, index) in analysisResults.news.articles" :key="index" class="news-item">
                      <h4>{{ article.title }}</h4>
                      <p>{{ article.summary }}</p>
                      <div class="news-meta">
                        <span>{{ article.source }}</span>
                        <span>{{ article.date }}</span>
                      </div>
                    </div>
                  </div>
                </a-card>
                <a-card :title="$t('dashboard.analysis.card.newsReport')" style="margin-top: 16px;" v-if="analysisResults.news?.report">
                  <div class="analysis-report" v-html="formatReport(analysisResults.news.report)"></div>
                </a-card>
              </div>
            </div>

            <!-- Sentiment -->
            <div v-else-if="agents[selectedAgentIndex].resultKey === 'sentiment' && analysisResults.sentiment" class="analysis-panel">
              <div class="sentiment-content">
                <a-card :title="$t('dashboard.analysis.card.sentimentIndicators')" v-if="analysisResults.sentiment?.scores">
                  <div class="sentiment-scores">
                    <div v-for="(score, source) in analysisResults.sentiment.scores" :key="source" class="sentiment-item">
                      <div class="sentiment-source">{{ source }}</div>
                      <a-progress :percent="score" :status="getSentimentStatus(score)" />
                    </div>
                  </div>
                </a-card>
                <a-card :title="$t('dashboard.analysis.card.sentimentReport')" style="margin-top: 16px;" v-if="analysisResults.sentiment?.report">
                  <div class="analysis-report" v-html="formatReport(analysisResults.sentiment.report)"></div>
                </a-card>
              </div>
            </div>

            <!-- Risk -->
            <div v-else-if="agents[selectedAgentIndex].resultKey === 'risk' && analysisResults.risk" class="analysis-panel">
              <div class="risk-content">
                <a-card :title="$t('dashboard.analysis.card.riskMetrics')" v-if="analysisResults.risk?.metrics">
                  <div class="risk-metrics">
                    <div v-for="(value, key) in analysisResults.risk.metrics" :key="key" class="risk-item">
                      <div class="risk-label">{{ key }}</div>
                      <div class="risk-value" :class="getRiskClass(value)">
                        {{ value }}
                      </div>
                    </div>
                  </div>
                </a-card>
                <a-card :title="$t('dashboard.analysis.card.riskReport')" style="margin-top: 16px;" v-if="analysisResults.risk?.report">
                  <div class="analysis-report" v-html="formatReport(analysisResults.risk.report)"></div>
                </a-card>
              </div>
            </div>

            <!-- Debate Bull (看涨研究员) -->
            <div v-else-if="agents[selectedAgentIndex].resultKey === 'debate_bull' && analysisResults.debate?.bull" class="analysis-panel">
              <div class="debate-content">
                <a-card :title="$t('dashboard.analysis.card.bullView')" class="bull-card" :headStyle="{ color: '#52c41a' }">
                  <div>
                    <div class="confidence-tag" style="margin-bottom: 12px;">
                      <a-tag color="green">{{ $t('dashboard.analysis.score.confidence') }}: {{ analysisResults.debate.bull.confidence }}%</a-tag>
                    </div>
                    <div class="key-points" v-if="analysisResults.debate.bull.key_points && analysisResults.debate.bull.key_points.length">
                      <h4>{{ $t('dashboard.analysis.label.keyPoints') }}：</h4>
                      <ul>
                        <li v-for="(point, idx) in analysisResults.debate.bull.key_points" :key="idx">{{ point }}</li>
                      </ul>
                    </div>
                    <div class="argument-body analysis-report" v-html="formatReport(analysisResults.debate.bull.argument)"></div>
                  </div>
                </a-card>
              </div>
            </div>

            <!-- Debate Bear (看跌研究员) -->
            <div v-else-if="agents[selectedAgentIndex].resultKey === 'debate_bear' && analysisResults.debate?.bear" class="analysis-panel">
              <div class="debate-content">
                <a-card :title="$t('dashboard.analysis.card.bearView')" class="bear-card" :headStyle="{ color: '#ff4d4f' }">
                  <div>
                    <div class="confidence-tag" style="margin-bottom: 12px;">
                      <a-tag color="red">{{ $t('dashboard.analysis.score.confidence') }}: {{ analysisResults.debate.bear.confidence }}%</a-tag>
                    </div>
                    <div class="key-points" v-if="analysisResults.debate.bear.key_points && analysisResults.debate.bear.key_points.length">
                      <h4>{{ $t('dashboard.analysis.label.keyPoints') }}：</h4>
                      <ul>
                        <li v-for="(point, idx) in analysisResults.debate.bear.key_points" :key="idx">{{ point }}</li>
                      </ul>
                    </div>
                    <div class="argument-body analysis-report" v-html="formatReport(analysisResults.debate.bear.argument)"></div>
                  </div>
                </a-card>
              </div>
            </div>

            <!-- Debate Research (研究经理) -->
            <div v-else-if="agents[selectedAgentIndex].resultKey === 'debate_research' && analysisResults.debate?.research_decision" class="analysis-panel">
              <div class="debate-content">
                <a-card :title="$t('dashboard.analysis.card.researchConclusion')" :style="{ borderLeft: '4px solid var(--primary-color)' }">
                  <div class="analysis-report">
                    {{ analysisResults.debate.research_decision }}
                  </div>
                </a-card>
              </div>
            </div>

            <!-- Trader Decision -->
            <div v-else-if="agents[selectedAgentIndex].resultKey === 'trader_decision' && analysisResults.trader_decision" class="analysis-panel">
              <div class="decision-content">
                <a-card :title="$t('dashboard.analysis.card.traderPlan')" style="margin-bottom: 16px;">
                  <div style="display: flex; gap: 20px;">
                    <div style="flex: 1;">
                      <div class="decision-header" style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                        <span
                          style="font-size: 24px; font-weight: bold;"
                          :style="{ color: analysisResults.trader_decision.decision === 'BUY' ? '#52c41a' : (analysisResults.trader_decision.decision === 'SELL' ? '#ff4d4f' : '#faad14') }"
                        >
                          {{ analysisResults.trader_decision.decision }}
                        </span>
                        <a-tag>{{ $t('dashboard.analysis.score.confidence') }}: {{ analysisResults.trader_decision.confidence }}%</a-tag>
                      </div>
                      <div class="analysis-report" v-html="formatReport(analysisResults.trader_decision.reasoning)"></div>
                    </div>
                    <div style="flex: 1; background: var(--summary-bg, var(--panel-bg)); padding: 16px; border-radius: 8px;" v-if="analysisResults.trader_decision.trading_plan">
                      <h4 style="color: var(--text-color);">{{ $t('dashboard.analysis.card.tradePlanDetail') }}</h4>
                      <div class="plan-item" v-for="(val, key) in analysisResults.trader_decision.trading_plan" :key="key" style="margin-top: 8px;">
                        <span style="color: var(--text-color); opacity: 0.6;">{{ getTradingPlanLabel(key) }}: </span>
                        <span style="font-weight: 500; color: var(--text-color);">{{ val }}</span>
                      </div>
                    </div>
                  </div>
                </a-card>
              </div>
            </div>

            <!-- Risk Debate -->
            <div v-else-if="agents[selectedAgentIndex].resultKey === 'risk_debate' && analysisResults.risk_debate" class="analysis-panel">
              <div class="decision-content">
                <a-card :title="$t('dashboard.analysis.card.riskDebate')" style="margin-bottom: 16px;">
                  <a-collapse>
                    <a-collapse-panel key="1" :header="$t('dashboard.analysis.risk.risky')">
                      <div class="analysis-report" v-html="formatReport(analysisResults.risk_debate.risky?.argument)"></div>
                      <div style="margin-top: 8px; font-weight: bold; color: var(--text-color);">{{ $t('dashboard.analysis.risk.conclusion') }}: {{ analysisResults.risk_debate.risky?.recommendation }}</div>
                    </a-collapse-panel>
                    <a-collapse-panel key="2" :header="$t('dashboard.analysis.risk.neutral')">
                      <div class="analysis-report" v-html="formatReport(analysisResults.risk_debate.neutral?.argument)"></div>
                      <div style="margin-top: 8px; font-weight: bold; color: var(--text-color);">{{ $t('dashboard.analysis.risk.conclusion') }}: {{ analysisResults.risk_debate.neutral?.recommendation }}</div>
                    </a-collapse-panel>
                    <a-collapse-panel key="3" :header="$t('dashboard.analysis.risk.safe')">
                      <div class="analysis-report" v-html="formatReport(analysisResults.risk_debate.safe?.argument)"></div>
                      <div style="margin-top: 8px; font-weight: bold; color: var(--text-color);">{{ $t('dashboard.analysis.risk.conclusion') }}: {{ analysisResults.risk_debate.safe?.recommendation }}</div>
                    </a-collapse-panel>
                  </a-collapse>
                </a-card>
              </div>
            </div>

            <!-- Final Decision -->
            <div v-else-if="agents[selectedAgentIndex].resultKey === 'final_decision' && analysisResults.final_decision" class="analysis-panel">
              <div class="decision-content">
                <a-card :title="$t('dashboard.analysis.card.finalDecision')" :headStyle="{ background: 'var(--summary-bg, var(--panel-bg))', color: 'var(--primary-color)' }">
                  <div>
                    <div class="final-decision-header" style="text-align: center; margin-bottom: 24px;">
                      <div
                        style="font-size: 36px; font-weight: 800; margin-bottom: 8px;"
                        :style="{ color: analysisResults.final_decision.decision === 'BUY' ? '#52c41a' : (analysisResults.final_decision.decision === 'SELL' ? '#ff4d4f' : '#faad14') }"
                      >
                        {{ analysisResults.final_decision.decision }}
                      </div>
                      <div style="color: var(--text-color);">{{ $t('dashboard.analysis.score.overall') }} {{ $t('dashboard.analysis.score.confidence') }}: {{ analysisResults.final_decision.confidence }}%</div>
                    </div>
                    <div class="analysis-report" v-html="formatReport(analysisResults.final_decision.reasoning)"></div>
                    <div style="margin-top: 16px; padding: 12px; background: var(--summary-bg, var(--panel-bg)); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-color);">
                      <strong>{{ $t('dashboard.analysis.label.riskWarning') }}：</strong> {{ analysisResults.final_decision.recommendation }}
                    </div>
                  </div>
                </a-card>
              </div>
            </div>

            <!-- 无结果提示 -->
            <div v-else class="no-result-hint">
              <a-empty :description="$t('dashboard.analysis.empty.noResult')" />
            </div>
          </div>
          <!-- 默认提示：点击人物查看结果 -->
          <div v-else class="select-hint">
            <a-empty :description="$t('dashboard.analysis.empty.selectAgent')" />
          </div>
        </div>
      </div>

      <!-- 右侧：核心展示区 + 终端（仅在非结果展示时显示） -->
      <div class="right-panel" v-if="!hasResult && !hasAnalysisResults">
        <div class="center-stage">
          <!-- Moved Header Info -->
          <!-- Header info removed -->
          <!-- 待机状态：输入框 (Removed, Replaced with Empty State) -->
          <div v-if="currentStep === 0 && !hasResult && !hasAnalysisResults" class="idle-interface">
            <div class="empty-state">
              <div class="empty-content">
                <div class="empty-icon">
                  <div class="icon-circle">
                    <a-icon type="thunderbolt" />
                  </div>
                </div>
                <p>{{ $t('dashboard.analysis.empty.selectSymbolDesc') }}</p>
                <div class="empty-features-wrapper">
                  <div class="empty-features">
                    <div class="features-track">
                      <div class="feature-item">
                        <a-icon type="read" />
                        <span>{{ $t('dashboard.analysis.feature.fundamental') }}</span>
                      </div>
                      <div class="feature-item">
                        <a-icon type="line-chart" />
                        <span>{{ $t('dashboard.analysis.feature.technical') }}</span>
                      </div>
                      <div class="feature-item">
                        <a-icon type="file-text" />
                        <span>{{ $t('dashboard.analysis.feature.news') }}</span>
                      </div>
                      <div class="feature-item">
                        <a-icon type="heart" />
                        <span>{{ $t('dashboard.analysis.feature.sentiment') }}</span>
                      </div>
                      <div class="feature-item">
                        <a-icon type="warning" />
                        <span>{{ $t('dashboard.analysis.feature.risk') }}</span>
                      </div>
                      <!-- 复制一份以实现无缝循环 -->
                      <div class="feature-item">
                        <a-icon type="read" />
                        <span>{{ $t('dashboard.analysis.feature.fundamental') }}</span>
                      </div>
                      <div class="feature-item">
                        <a-icon type="line-chart" />
                        <span>{{ $t('dashboard.analysis.feature.technical') }}</span>
                      </div>
                      <div class="feature-item">
                        <a-icon type="file-text" />
                        <span>{{ $t('dashboard.analysis.feature.news') }}</span>
                      </div>
                      <div class="feature-item">
                        <a-icon type="heart" />
                        <span>{{ $t('dashboard.analysis.feature.sentiment') }}</span>
                      </div>
                      <div class="feature-item">
                        <a-icon type="warning" />
                        <span>{{ $t('dashboard.analysis.feature.risk') }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 运行状态：可视化动态 -->
          <div v-if="currentStep > 0 && !hasResult && !hasAnalysisResults" class="running-interface">
            <!-- AI金融科技特效 -->
            <div class="vis-container">
              <!-- 深色科技背景 -->
              <div class="tech-background">
                <!-- 像素风格猫 -->
                <!-- <div class="pixel-cat">
                  <div class="cat-body"></div>
                  <div class="cat-head"></div>
                  <div class="cat-ear cat-ear-left"></div>
                  <div class="cat-ear cat-ear-right"></div>
                  <div class="cat-eye cat-eye-left"></div>
                  <div class="cat-eye cat-eye-right"></div>
                  <div class="cat-nose"></div>
                  <div class="cat-mouth"></div>
                  <div class="cat-tail"></div>
                </div> -->

                <!-- 神经网络连接线 -->
                <svg class="neural-network" viewBox="0 0 400 400" preserveAspectRatio="xMidYMid meet">
                  <defs>
                    <linearGradient id="neuralGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" style="stop-color:rgba(24, 144, 255, 0.6);stop-opacity:1" />
                      <stop offset="50%" style="stop-color:rgba(114, 46, 209, 0.4);stop-opacity:1" />
                      <stop offset="100%" style="stop-color:rgba(24, 144, 255, 0.6);stop-opacity:1" />
                    </linearGradient>
                  </defs>
                  <!-- 连接线 -->
                  <path
                    v-for="(path, i) in 8"
                    :key="i"
                    class="neural-path"
                    :d="getNeuralPath(i)"
                    stroke="url(#neuralGradient)"
                    stroke-width="1.5"
                    fill="none"
                    opacity="0.4"
                  />
                  <!-- 节点 -->
                  <circle
                    v-for="(node, i) in 12"
                    :key="i"
                    class="neural-node"
                    :cx="getNodeX(i)"
                    :cy="getNodeY(i)"
                    r="4"
                    fill="var(--primary-color)"
                  />
                </svg>

                <!-- 数据矩阵雨效果 -->
                <div class="matrix-rain">
                  <div v-for="i in 20" :key="i" class="matrix-column" :style="getMatrixColumnStyle(i)" :data-char="getMatrixChar(i)"></div>
                </div>
              </div>

              <!-- 核心内容 -->
              <div class="holo-core">
                <div class="core-icon">
                  <div class="ai-hologram">
                    <div class="hologram-ring ring-1"></div>
                    <div class="hologram-ring ring-2"></div>
                    <div class="hologram-ring ring-3"></div>
                    <img :src="`https://api.dicebear.com/7.x/avataaars/svg?seed=${agents[currentStep - 1]?.name}&backgroundColor=b6e3f4,c0aede,d1d4f9,ffd5dc,ffdfbf&accessories=prescription01,prescription02&accessoriesColor=262e33,65c9ff,a7ffc4,e6e6e6,ffdeb5,ffffb1&clothing=blazerAndSweater,blazerAndShirt,collarAndSweater,graphicShirt,hoodie&clothingGraphic=bear,cumbia,deer,diamond,hola,pizza,resist&eyebrows=defaultNatural,raisedExcited,sadConcernedNatural&eyes=squint&facialHair[]&hairColor=2c1b18,4a312c,724133,a55728,b58143,c93305,d6b370,ecdcbf,e8e1e1,f59797&mouth=smile,twinkle&top=bigHair,curvy,miaWallace,shortWaved,straightAndStrand,longButNotTooLong,shaggy,shaggyMullet,shortCurly,straight01`" class="core-avatar" v-if="agents[currentStep - 1]" />
                    <div class="hologram-scan-line"></div>
                  </div>
                </div>
                <div class="holo-content">
                  <div class="current-task-label">
                    <span class="label-prefix">[AI]</span>
                    {{ $t('ai-analysis.vis.stage') }} {{ getStageNumber(currentStep) }} {{ $t('ai-analysis.vis.processing') }}
                  </div>
                  <div class="current-agent-name">{{ $t(agents[currentStep - 1]?.nameKey) }}</div>
                  <div class="current-task-detail">{{ currentLog }}</div>
                </div>
              </div>

              <!-- 金融数据可视化 -->
              <div class="financial-visualization">
                <!-- 实时K线图 -->
                <svg class="candlestick-chart" viewBox="0 0 400 150" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="chartGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" style="stop-color:rgba(24, 144, 255, 0.4);stop-opacity:1" />
                      <stop offset="100%" style="stop-color:rgba(24, 144, 255, 0);stop-opacity:0" />
                    </linearGradient>
                    <filter id="glow">
                      <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                      <feMerge>
                        <feMergeNode in="coloredBlur"/>
                        <feMergeNode in="SourceGraphic"/>
                      </feMerge>
                    </filter>
                  </defs>
                  <!-- 网格线 -->
                  <g class="chart-grid">
                    <line
                      v-for="i in 5"
                      :key="i"
                      x1="0"
                      :y1="i * 30"
                      x2="400"
                      :y2="i * 30"
                      stroke="rgba(24, 144, 255, 0.1)"
                      stroke-width="1"/>
                  </g>
                  <!-- K线 -->
                  <g v-for="(candle, i) in 12" :key="i" class="candlestick">
                    <line
                      :x1="i * 30 + 15"
                      :y1="getCandleHigh(i)"
                      :x2="i * 30 + 15"
                      :y2="getCandleLow(i)"
                      stroke="rgba(24, 144, 255, 0.6)"
                      stroke-width="1"/>
                    <rect
                      :x="i * 30 + 10"
                      :y="getCandleOpen(i)"
                      :width="10"
                      :height="Math.abs(getCandleOpen(i) - getCandleClose(i))"
                      :fill="getCandleColor(i)"
                      stroke="rgba(24, 144, 255, 0.8)"
                      stroke-width="1"/>
                  </g>
                  <!-- 价格线 -->
                  <path
                    class="price-line"
                    :d="getPriceLinePath()"
                    fill="none"
                    stroke="rgba(24, 144, 255, 0.8)"
                    stroke-width="2"
                    filter="url(#glow)"/>
                </svg>
              </div>

              <!-- AI分析指标 -->
              <!-- <div class="ai-metrics">
                <div v-for="(metric, i) in 4" :key="i" class="metric-card">
                  <div class="metric-label">{{ getMetricLabel(i) }}</div>
                  <div class="metric-value">{{ getMetricValue(i) }}</div>
                  <div class="metric-bar">
                    <div class="metric-fill" :style="getMetricBarStyle(i)"></div>
                  </div>
                </div>
              </div> -->

              <!-- 全息投影边框 -->
              <div class="hologram-border">
                <div class="border-corner corner-tl">
                  <div class="corner-line corner-line-h"></div>
                  <div class="corner-line corner-line-v"></div>
                </div>
                <div class="border-corner corner-tr">
                  <div class="corner-line corner-line-h"></div>
                  <div class="corner-line corner-line-v"></div>
                </div>
                <div class="border-corner corner-bl">
                  <div class="corner-line corner-line-h"></div>
                  <div class="corner-line corner-line-v"></div>
                </div>
                <div class="border-corner corner-br">
                  <div class="corner-line corner-line-h"></div>
                  <div class="corner-line corner-line-v"></div>
                </div>
              </div>
            </div>
          </div>

          <!-- 结果状态：报告概览（仅在没有中间面板时显示） -->
          <div v-if="hasResult && !hasAnalysisResults" class="result-interface">
            <div class="result-card">
              <div class="result-header">
                <div class="asset-title">{{ symbol }} {{ $t('ai-analysis.result.complete') }}</div>
                <div class="timestamp">{{ new Date().toLocaleString() }}</div>
              </div>

              <div class="result-body">
                <!-- Removed detailed result box as this component is now primarily for loading/idle -->
                <div class="summary-text">{{ $t('ai-analysis.vis.processing') }}...</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 右侧/底部：系统日志终端（仅在非结果展示时显示） -->
        <div class="terminal-panel" v-if="!hasResult && !hasAnalysisResults">
          <div class="terminal-header">
            <a-icon type="code" :style="{ color: 'var(--primary-color)' }" /> {{ $t('ai-analysis.logs.title') }}
          </div>
          <div class="terminal-window" ref="terminalWindow">
            <div v-for="(log, idx) in logs" :key="idx" class="log-line">
              <span class="log-time">[{{ log.time }}]</span>
              <span class="log-source" :style="{ color: log.color }">{{ log.source }}:</span>
              <span class="log-msg">{{ log.message }}</span>
            </div>
            <div class="cursor-blink">_</div>
          </div>
        </div>
      </div>

    </div>

  </div>
</template>

<script>
import { getAnalysisTaskStatus } from '@/api/market'
import { Collapse } from 'ant-design-vue'

export default {
  components: {
    'a-collapse': Collapse,
    'a-collapse-panel': Collapse.Panel
  },
  name: 'MetaverseAnalysis',
  props: {
    symbol: {
      type: String,
      default: ''
    },
    analyzing: {
      type: Boolean,
      default: false
    },
    taskId: {
      type: [Number, String],
      default: null,
      validator: function (value) {
        return value === null || value === undefined || !isNaN(Number(value))
      }
    },
    analysisResults: {
      type: Object,
      default: () => ({
        overview: null,
        fundamental: null,
        technical: null,
        news: null,
        sentiment: null,
        risk: null,
        debate: null,
        trader_decision: null,
        risk_debate: null,
        final_decision: null
      })
    }
  },
  data () {
    return {
      currentStep: 0, // 0: Idle, 1-N: Agents Working
      hasResult: false,
      logs: [],
      currentLog: '',
      taskStatusTimer: null, // 任务状态轮询定时器
      agentStatusMap: {}, // 记录每个 agent 的执行状态
      taskStartTime: null, // 任务开始时间
      selectedAgentIndex: null, // 当前选中的 agent 索引
      simulationTimer: null, // 模拟执行定时器
      currentSimulationAgentIndex: null, // 当前模拟执行的 agent 索引

      agents: [
        {
          name: 'Fundamental Analyst',
          nameKey: 'ai-analysis.agent.fundamental',
          roleKey: 'ai-analysis.agent.role.fundamental',
          color: '#faad14',
          scripts: ['ai-analysis.script.fundamental'],
          resultKey: 'fundamental' // 对应 fundamental 标签
        },
        {
          name: 'Technical Analyst',
          nameKey: 'ai-analysis.agent.technical',
          roleKey: 'ai-analysis.agent.role.technical',
          color: '#1890ff',
          scripts: ['ai-analysis.script.technical'],
          resultKey: 'technical' // 对应 technical 标签
        },
        {
          name: 'News Analyst',
          nameKey: 'ai-analysis.agent.news',
          roleKey: 'ai-analysis.agent.role.news',
          color: '#13c2c2',
          scripts: ['ai-analysis.script.news'],
          resultKey: 'news' // 对应 news 标签
        },
        {
          name: 'Sentiment Analyst',
          nameKey: 'ai-analysis.agent.sentiment',
          roleKey: 'ai-analysis.agent.role.sentiment',
          color: '#eb2f96',
          scripts: ['ai-analysis.script.sentiment'],
          resultKey: 'sentiment' // 对应 sentiment 标签
        },
        {
          name: 'Risk Analyst',
          nameKey: 'ai-analysis.agent.risk',
          roleKey: 'ai-analysis.agent.role.risk',
          color: '#f5222d',
          scripts: ['ai-analysis.script.risk'],
          resultKey: 'risk' // 对应 risk 标签
        },
        {
          name: 'Bull Researcher',
          nameKey: 'ai-analysis.agent.bull',
          roleKey: 'ai-analysis.agent.role.bull',
          color: '#52c41a',
          scripts: ['ai-analysis.panel.thinking'],
          resultKey: 'debate_bull' // 对应 debate.bull（看涨部分）
        },
        {
          name: 'Bear Researcher',
          nameKey: 'ai-analysis.agent.bear',
          roleKey: 'ai-analysis.agent.role.bear',
          color: '#f5222d',
          scripts: ['ai-analysis.panel.thinking'],
          resultKey: 'debate_bear' // 对应 debate.bear（看跌部分）
        },
        {
          name: 'Research Manager',
          nameKey: 'ai-analysis.agent.manager',
          roleKey: 'ai-analysis.agent.role.manager',
          color: '#722ed1',
          scripts: ['ai-analysis.panel.thinking'],
          resultKey: 'debate_research' // 对应 debate.research_decision（研究结论）
        },
        {
          name: 'Trader Agent',
          nameKey: 'ai-analysis.agent.trader',
          roleKey: 'ai-analysis.agent.role.trader',
          color: '#1890ff',
          scripts: ['ai-analysis.panel.thinking'],
          resultKey: 'trader_decision' // 对应 trader_decision
        },
        {
          name: 'Risky Analyst',
          nameKey: 'ai-analysis.agent.risky',
          roleKey: 'ai-analysis.agent.role.risky',
          color: '#ffec3d',
          scripts: ['ai-analysis.panel.thinking'],
          resultKey: 'risk_debate' // 对应 risk_debate（risky）
        },
        {
          name: 'Neutral Analyst',
          nameKey: 'ai-analysis.agent.neutral',
          roleKey: 'ai-analysis.agent.role.neutral',
          color: '#8c8c8c',
          scripts: ['ai-analysis.panel.thinking'],
          resultKey: 'risk_debate' // 对应 risk_debate（neutral）
        },
        {
          name: 'Safe Analyst',
          nameKey: 'ai-analysis.agent.safe',
          roleKey: 'ai-analysis.agent.role.safe',
          color: '#52c41a',
          scripts: ['ai-analysis.panel.thinking'],
          resultKey: 'risk_debate' // 对应 risk_debate（safe）
        },
        {
          name: 'Risk Manager (CRO)',
          nameKey: 'ai-analysis.agent.cro',
          roleKey: 'ai-analysis.agent.role.cro',
          color: '#fa541c',
          scripts: ['ai-analysis.panel.thinking'],
          resultKey: 'final_decision' // 对应 final_decision
        },
        {
          name: 'Investment Director',
          nameKey: 'ai-analysis.agent.investment_director',
          roleKey: 'ai-analysis.agent.role.investment_director',
          color: 'var(--neon-main)',
          scripts: ['ai-analysis.script.market'],
          resultKey: 'overview' // 对应 overview 标签（最终结论），放在最后以便反转后显示在最上面
        }
      ]
    }
  },
  computed: {
    // 反转 agents 数组，实现从下往上的显示
    reversedAgents () {
      return [...this.agents].reverse()
    },
    // 检查是否有分析结果数据
    hasAnalysisResults () {
      if (!this.analysisResults) return false
      return !!(
        this.analysisResults.overview ||
        this.analysisResults.fundamental ||
        this.analysisResults.technical ||
        this.analysisResults.news ||
        this.analysisResults.sentiment ||
        this.analysisResults.risk ||
        this.analysisResults.debate?.bull ||
        this.analysisResults.debate?.bear ||
        this.analysisResults.debate?.research_decision ||
        this.analysisResults.trader_decision ||
        this.analysisResults.risk_debate ||
        this.analysisResults.final_decision
      )
    },
    theme () {
      return this.$store.getters.theme
    },
    primaryColor () {
      return this.$store.state.app.color || '#1890ff'
    },
    currentStageName () {
      if (this.currentStep === 0) return this.$t('ai-analysis.stage.idle')
      if (this.currentStep <= 5) return this.$t('ai-analysis.stage.1')
      if (this.currentStep <= 8) return this.$t('ai-analysis.stage.2')
      if (this.currentStep === 9) return this.$t('ai-analysis.stage.3')
      if (this.currentStep <= 13) return this.$t('ai-analysis.stage.4')
      return this.$t('ai-analysis.stage.complete')
    },
    cssVars () {
      const isDark = this.theme === 'dark' || this.theme === 'realdark'
      const primary = this.primaryColor

      // 将主题色转换为 rgba 格式用于 hover 效果
      const hexToRgb = (hex) => {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
        return result ? {
          r: parseInt(result[1], 16),
          g: parseInt(result[2], 16),
          b: parseInt(result[3], 16)
        } : { r: 24, g: 144, b: 255 }
      }
      const rgb = hexToRgb(primary)

      if (isDark) {
        // 暗色模式下，使用主题色但稍微亮一点
        return {
          '--bg-color': '#0a0b10',
          '--panel-bg': '#131722',
          '--text-color': '#d1d4dc',
          '--neon-main': primary,
          '--primary-color': primary,
          '--border-color': '#2a2e39',
          '--header-bg': 'rgba(19, 23, 34, 0.9)',
          '--center-bg': 'rgba(19, 23, 34, 0.5)',
          '--terminal-bg': 'rgba(0, 0, 0, 0.5)',
          '--terminal-header-bg': '#1f1f1f',
          '--card-bg': 'rgba(19, 23, 34, 0.95)',
          '--input-bg': 'rgba(0, 0, 0, 0.5)',
          '--shadow-color': 'rgba(0, 0, 0, 0.5)',
          '--particle-color': primary,
          '--empty-bg': 'rgba(255, 255, 255, 0.05)',
          '--empty-border': 'rgba(255, 255, 255, 0.1)',
          '--empty-hover-bg': `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.1)`,
          '--empty-hover-border': `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.15)`,
          '--icon-color': primary,
          '--link-color': primary,
          '--link-hover-color': `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.8)`
        }
      } else {
         return {
          '--bg-color': '#f0f2f5',
          '--panel-bg': '#ffffff',
          '--text-color': 'rgba(0, 0, 0, 0.85)',
          '--neon-main': primary,
          '--primary-color': primary,
          '--border-color': '#d9d9d9',
          '--header-bg': 'rgba(255, 255, 255, 0.9)',
          '--center-bg': 'rgba(255, 255, 255, 0.6)',
          '--terminal-bg': 'rgba(255, 255, 255, 0.8)',
          '--terminal-header-bg': '#fafafa',
          '--card-bg': 'rgba(255, 255, 255, 0.95)',
          '--input-bg': '#ffffff',
          '--shadow-color': 'rgba(0, 0, 0, 0.1)',
          '--particle-color': primary,
          '--summary-bg': '#f5f5f5',
          '--empty-bg': 'rgba(0, 0, 0, 0.02)',
          '--empty-border': 'rgba(0, 0, 0, 0.06)',
          '--empty-hover-bg': `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.1)`,
          '--empty-hover-border': `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.2)`,
          '--icon-color': primary,
          '--link-color': primary,
          '--link-hover-color': `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.8)`
        }
      }
    }
  },
  watch: {
    analyzing: {
      handler (val) {
        if (val) {
          this.startAnalysis()
        } else {
          // 停止模拟执行
          if (this.simulationTimer) {
            clearTimeout(this.simulationTimer)
            this.simulationTimer = null
          }
          // 只有在没有分析结果数据时才重置（避免影响历史记录查看）
          if (!this.hasAnalysisResults) {
            this.reset()
          }
          // If analysis stopped with results, mark all agents as completed
          if (this.hasAnalysisResults) {
            for (let i = 0; i < this.agents.length; i++) {
              if (this.agentStatusMap[i] !== 'completed') {
                this.agentStatusMap[i] = 'completed'
              }
            }
            this.hasResult = true
            this.currentStep = this.agents.length + 1
            this.selectFirstAvailableAgent()
          }
        }
      },
      immediate: true
    },
    taskId: {
      handler (val) {
        if (val && this.analyzing) {
          this.startTaskStatusPolling()
        } else {
          this.stopTaskStatusPolling()
        }
      },
      immediate: true
    },
    analysisResults: {
      handler (val) {
        // 当有结果时（任务完成或查看历史记录），自动选择第一个有结果的 agent
        if (val && this.hasAnalysisResults) {
          // 如果是历史记录查看模式（有结果但不在分析中），标记所有 agent 为完成状态
          if (!this.analyzing && !this.hasResult) {
            for (let i = 0; i < this.agents.length; i++) {
              this.agentStatusMap[i] = 'completed'
            }
            this.currentStep = this.agents.length + 1
            // 不设置 hasResult，因为这是历史记录查看，不是新任务完成
            // 但我们需要显示结果，所以使用 hasAnalysisResults 来控制显示
          }
          // 自动选择第一个有结果的 agent
          if (this.selectedAgentIndex === null) {
            this.$nextTick(() => {
              this.selectFirstAvailableAgent()
            })
          }
        } else if (!val || !this.hasAnalysisResults) {
          // 如果没有结果数据，重置状态
          if (!this.analyzing) {
            this.selectedAgentIndex = null
          }
        }
      },
      deep: true,
      immediate: true
    }
  },
  mounted () {
    this.addLog('SYSTEM', 'ZhiYiQuant Quantum Core Initialized.', '#52c41a')
    this.addLog('SYSTEM', 'Awaiting target coordinates...', '#8c8c8c')
  },
  beforeDestroy () {
    this.stopTaskStatusPolling()
  },
  methods: {
    addLog (source, message, color) {
      const time = new Date().toLocaleTimeString('en-US', { hour12: false })
      this.logs.push({ time, source, message, color })
      this.$nextTick(() => {
        const terminal = this.$refs.terminalWindow
        if (terminal) terminal.scrollTop = terminal.scrollHeight
      })
    },

    startAnalysis () {
      // 重置所有状态
      this.currentStep = 0
      this.hasResult = false
      this.logs = []
      this.agentStatusMap = {}
      this.taskStartTime = Date.now()
      this.currentSimulationAgentIndex = null

      // 停止之前的模拟
      if (this.simulationTimer) {
        clearTimeout(this.simulationTimer)
        this.simulationTimer = null
      }

      // 初始化所有 agent 为 waiting 状态
      for (let i = 0; i < this.agents.length; i++) {
        this.agentStatusMap[i] = 'waiting'
      }

      this.addLog('SYSTEM', `Initiating Quantum Analysis for ${this.symbol || 'DEMO'}...`, 'var(--neon-main)')

      // 初始时滚动到底部，显示第一个要执行的 agent（Fundamental Analyst，显示在最下面）
      this.$nextTick(() => {
        const listContainer = this.$refs.agentsList
        if (listContainer) {
          setTimeout(() => {
            listContainer.scrollTop = listContainer.scrollHeight
          }, 100)
        }
      })

      // Start simulation animation while backend processes
      this.addLog('SYSTEM', 'Starting multi-agent analysis...', '#52c41a')
      // Small delay before starting simulation for visual effect
      setTimeout(() => {
        if (this.analyzing) {
          this.startSimulation()
        }
      }, 500)
    },

    // 开始模拟执行
    startSimulation () {
      // 初始化所有 agent 状态为 waiting
      for (let i = 0; i < this.agents.length; i++) {
        this.agentStatusMap[i] = 'waiting'
      }
      // 从第一个 agent 开始（数组第一个，反转后显示在最下面）
      // 执行顺序：从下向上，从索引0（Fundamental Analyst）到索引最后（Investment Director）
      const startIndex = 0
      this.runSimulationStep(startIndex)
    },

    // 模拟执行步骤
    runSimulationStep (agentIndex) {
      if (!this.analyzing) {
        return
      }

      // 如果已经执行完所有 agent（索引超出范围）
      // 这种情况不应该发生，因为最后一个 agent 会在自己的定时器中处理
      if (agentIndex >= this.agents.length) {
        this.addLog('SYSTEM', 'All agents completed. Waiting for final results...', '#faad14')
        // 开始轮询真实结果
        if (this.taskId) {
          this.startTaskStatusPolling()
        }
        return
      }

      // 确保前面的 agent 都已完成（除了第一个）
      // 对于投资总监（最后一个agent），必须确保所有前面的agent都已完成
      if (agentIndex > 0) {
        // 检查前面的 agent 是否都已完成
        let allPreviousCompleted = true
        for (let i = 0; i < agentIndex; i++) {
          if (this.agentStatusMap[i] !== 'completed') {
            allPreviousCompleted = false
            break
          }
        }
        // 如果前面的 agent 还没完成，等待一下再试
        if (!allPreviousCompleted) {
          this.simulationTimer = setTimeout(() => {
            if (this.analyzing) {
              this.runSimulationStep(agentIndex)
            }
          }, 500)
          return
        }
      }

      // 激活当前 agent
      this.agentStatusMap[agentIndex] = 'active'
      this.currentStep = agentIndex + 1
      this.currentSimulationAgentIndex = agentIndex

      const agent = this.agents[agentIndex]
      this.addLog('SYSTEM', `Activating Node: ${agent.name}`, agent.color)
      this.currentLog = this.$t(agent.scripts[0]) || agent.scripts[0] || this.$t('ai-analysis.panel.thinking')

      // 滚动到当前 agent（只滚动列表容器）
      this.$nextTick(() => {
        this.scrollToAgent(agentIndex)
      })

      // 随机执行时长（3-7秒）
      const randomDuration = 3000 + Math.random() * 4000 // 3000-7000ms

      // 如果是最后一个 agent（Investment Director），需要等待真实数据
      const isLastAgent = agentIndex === this.agents.length - 1

      this.simulationTimer = setTimeout(() => {
        if (!this.analyzing) {
          return
        }

        // 如果是最后一个 agent，需要等待真实数据
        if (isLastAgent) {
          this.addLog('SYSTEM', 'Final agent processing. Waiting for backend results...', '#faad14')
          // 开始轮询真实结果
          if (this.taskId) {
            // 开始轮询，等待真实数据
            this.startTaskStatusPolling()
            // 保持 active 状态，不标记为完成，继续等待真实结果
            return
          } else {
            // If there is no taskId (sync backend call), DO NOT auto-complete after a fixed delay.
            // Instead, keep the last agent "active" until real analysisResults arrive,
            // so we don't enter result view with empty data (blank gap).
            const startedAt = Date.now()
            const maxWaitMs = 120000 // 2 minutes max wait
            const waitLoop = () => {
              if (!this.analyzing) return
              // Real results are considered ready when parent passes actual analysisResults content.
              if (this.hasAnalysisResults) {
                this.agentStatusMap[agentIndex] = 'completed'
                this.addLog(agent.name, 'Task completed', agent.color)
                this.hasResult = true
                this.selectFirstAvailableAgent()
                return
              }
              if (Date.now() - startedAt > maxWaitMs) {
                // Timeout fallback: complete to avoid infinite spinner, but keep UI stable.
                this.agentStatusMap[agentIndex] = 'completed'
                this.addLog('SYSTEM', 'Timeout waiting for backend results. Please retry.', '#faad14')
                this.hasResult = true
                this.selectFirstAvailableAgent()
                return
              }
              setTimeout(waitLoop, 500)
            }
            waitLoop()
            return
          }
        }

        // 标记当前 agent 为完成
        this.agentStatusMap[agentIndex] = 'completed'
        this.addLog(agent.name, 'Task completed', agent.color)

        // 继续下一个 agent（向上，索引加1，因为从下向上执行）
        this.runSimulationStep(agentIndex + 1)
      }, randomDuration) // 随机执行时长
    },

    // 滚动到指定的 agent（只滚动列表容器，不影响整个页面）
    scrollToAgent (agentIndex) {
      const el = document.getElementById('agent-' + agentIndex)
      const listContainer = this.$refs.agentsList
      if (el && listContainer) {
        // 检测是否为移动端（横向滚动）
        const isMobile = window.innerWidth <= 768
        const containerRect = listContainer.getBoundingClientRect()
        const elementRect = el.getBoundingClientRect()

        if (isMobile) {
          // 移动端：横向滚动，居中显示
          const scrollLeft = listContainer.scrollLeft
          const elementOffsetLeft = elementRect.left - containerRect.left + scrollLeft
          const containerWidth = listContainer.clientWidth
          const elementWidth = el.offsetWidth

          const targetScrollLeft = elementOffsetLeft - (containerWidth / 2) + (elementWidth / 2)
          listContainer.scrollTo({
            left: Math.max(0, targetScrollLeft),
            behavior: 'smooth'
          })
        } else {
          // 桌面端：纵向滚动，居中显示
          const scrollTop = listContainer.scrollTop
          const elementOffsetTop = elementRect.top - containerRect.top + scrollTop
          const containerHeight = listContainer.clientHeight
          const elementHeight = el.offsetHeight

          const targetScrollTop = elementOffsetTop - (containerHeight / 2) + (elementHeight / 2)
          listContainer.scrollTo({
            top: Math.max(0, targetScrollTop),
            behavior: 'smooth'
          })
        }
      }
    },

    // 开始轮询任务状态（仅在模拟完成后调用）
    startTaskStatusPolling () {
      if (this.taskStatusTimer) {
        clearInterval(this.taskStatusTimer)
      }

      const taskId = Number(this.taskId)
      if (!taskId) {
        return
      }

      // 立即执行一次
      this.pollTaskStatus()

      // 每2秒轮询一次
      this.taskStatusTimer = setInterval(() => {
        this.pollTaskStatus()
      }, 2000)
    },

    // 停止轮询任务状态
    stopTaskStatusPolling () {
      if (this.taskStatusTimer) {
        clearInterval(this.taskStatusTimer)
        this.taskStatusTimer = null
      }
    },

    // 轮询任务状态
    async pollTaskStatus () {
      if (!this.taskId || !this.analyzing) {
        return
      }

      try {
        const taskId = Number(this.taskId)
        if (!taskId) {
          return
        }
        const res = await getAnalysisTaskStatus({
          task_id: taskId
        })

        if (res && res.code === 1 && res.data) {
          const task = res.data

          if (task.status === 'completed') {
            // 任务完成，所有 agent 标记为完成（包括最后一个正在等待的）
            for (let i = 0; i < this.agents.length; i++) {
              this.agentStatusMap[i] = 'completed'
            }
            this.currentStep = this.agents.length + 1
            this.hasResult = true
            this.addLog('SYSTEM', 'Analysis complete. All agents finished.', '#52c41a')
            // 默认选中第一个有结果的 agent（投资总监，显示在最上面）
            this.selectFirstAvailableAgent()
            this.stopTaskStatusPolling()

            // 停止模拟定时器（如果还在运行）
            if (this.simulationTimer) {
              clearTimeout(this.simulationTimer)
              this.simulationTimer = null
            }

            // 更新分析结果（从任务结果中获取）
            if (task.result) {
              // 这里可以更新 analysisResults，但通常由父组件传递
            }
          } else if (task.status === 'failed') {
            // 任务失败
            this.addLog('SYSTEM', `Analysis failed: ${task.error_message || 'Unknown error'}`, '#f5222d')
            this.stopTaskStatusPolling()
          } else if (task.status === 'processing') {
            // 任务还在处理中
            // 检查是否所有前面的 agent 都已完成，只有都完成后才激活投资总监
            const lastAgentIndex = this.agents.length - 1
            let allPreviousCompleted = true

            // 检查投资总监之前的所有 agent 是否都已完成
            for (let i = 0; i < lastAgentIndex; i++) {
              if (this.agentStatusMap[i] !== 'completed') {
                allPreviousCompleted = false
                break
              }
            }

            // 只有所有前面的 agent 都完成后，才激活投资总监
            if (allPreviousCompleted && this.agentStatusMap[lastAgentIndex] !== 'completed') {
              // 如果投资总监还没有被激活，现在激活它
              if (this.agentStatusMap[lastAgentIndex] !== 'active') {
                this.agentStatusMap[lastAgentIndex] = 'active'
                this.currentStep = lastAgentIndex + 1
                this.currentSimulationAgentIndex = lastAgentIndex
                const agent = this.agents[lastAgentIndex]
                this.addLog('SYSTEM', `Activating Node: ${agent.name}`, agent.color)
                this.currentLog = this.$t(agent.scripts[0]) || agent.scripts[0] || this.$t('ai-analysis.panel.thinking')
              }
            }
            // 如果前面的 agent 还没完成，不激活投资总监，继续等待
          }
        }
      } catch (error) {
        // 继续轮询，不中断
      }
    },

    // 根据任务状态更新 agent 进度（仅在模拟完成后，等待真实结果时调用）
    updateAgentProgressFromTask (task) {
      // 这个方法现在只用于检查任务是否完成，不再更新进度
      // 进度由模拟执行控制
    },

    reset () {
      this.currentStep = 0
      this.hasResult = false
      this.logs = []
      this.agentStatusMap = {}
      this.taskStartTime = null
      this.selectedAgentIndex = null
      this.currentSimulationAgentIndex = null

      // 停止模拟和轮询
      if (this.simulationTimer) {
        clearTimeout(this.simulationTimer)
        this.simulationTimer = null
      }
      this.stopTaskStatusPolling()
    },

    // 获取粒子样式（支持idle和running两种状态）
    getParticleStyle (index) {
      // 如果index <= 20，说明是idle状态的粒子（20个）
      if (index <= 20) {
        return {
          left: Math.random() * 100 + '%',
          top: Math.random() * 100 + '%',
          animationDuration: (Math.random() * 5 + 5) + 's',
          animationDelay: (Math.random() * 2) + 's'
        }
      }
      // 否则是running状态的粒子（50个），使用圆形分布
      const angle = ((index - 1) / 50) * Math.PI * 2
      const radius = 150 + Math.random() * 100
      const x = 50 + Math.cos(angle) * radius
      const y = 50 + Math.sin(angle) * radius
      const delay = (index - 1) * 0.1
      const duration = 3 + Math.random() * 2
      return {
        left: `${x}%`,
        top: `${y}%`,
        animationDelay: `${delay}s`,
        animationDuration: `${duration}s`
      }
    },

    getStageNumber (step) {
      if (step <= 5) return 'I'
      if (step <= 8) return 'II'
      if (step === 9) return 'III'
      return 'IV'
    },

    // 获取数据流样式
    getDataStreamStyle (index) {
      const angles = [0, 60, 120, 180, 240, 300]
      const angle = angles[index - 1] || (index - 1) * 60
      const delay = index * 0.3
      return {
        transform: `rotate(${angle}deg)`,
        animationDelay: `${delay}s`
      }
    },

    // 获取神经网络路径
    getNeuralPath (index) {
      const paths = [
        'M50,100 Q100,50 150,100 T250,100',
        'M100,150 Q150,100 200,150 T300,150',
        'M150,200 Q200,150 250,200 T350,200',
        'M50,200 Q100,150 150,200 T250,200',
        'M100,50 Q150,100 200,50 T300,50',
        'M200,100 Q250,50 300,100 T400,100',
        'M150,100 Q200,150 250,100 T350,100',
        'M100,100 Q150,200 200,100 T300,100'
      ]
      return paths[index] || paths[0]
    },

    // 获取节点X坐标
    getNodeX (index) {
      const positions = [50, 100, 150, 200, 250, 300, 150, 200, 100, 250, 150, 300]
      return positions[index] || 200
    },

    // 获取节点Y坐标
    getNodeY (index) {
      const positions = [100, 150, 200, 100, 200, 150, 50, 50, 250, 250, 100, 200]
      return positions[index] || 150
    },

    // 获取矩阵列样式
    getMatrixColumnStyle (index) {
      const delay = index * 0.15
      const duration = 2 + Math.random() * 3
      return {
        left: `${(index / 20) * 100}%`,
        animationDelay: `${delay}s`,
        animationDuration: `${duration}s`
      }
    },

    // 获取矩阵字符
    getMatrixChar (index) {
      const chars = ['0', '1', '0', '1', '1', '0', '1', '0', '0', '1']
      return chars[index % chars.length]
    },

    // 获取K线高点
    getCandleHigh (index) {
      const base = 75
      const variation = Math.sin(index * 0.5) * 20
      return base - variation - 10
    },

    // 获取K线低点
    getCandleLow (index) {
      const base = 75
      const variation = Math.sin(index * 0.5) * 20
      return base - variation + 10
    },

    // 获取K线开盘价
    getCandleOpen (index) {
      const base = 75
      const variation = Math.sin(index * 0.5) * 20
      return base - variation - 3
    },

    // 获取K线收盘价
    getCandleClose (index) {
      const base = 75
      const variation = Math.sin((index + 0.5) * 0.5) * 20
      return base - variation + 3
    },

    // 获取K线颜色
    getCandleColor (index) {
      const open = this.getCandleOpen(index)
      const close = this.getCandleClose(index)
      return close > open ? 'rgba(82, 196, 26, 0.8)' : 'rgba(245, 34, 45, 0.8)'
    },

    // 获取价格线路径
    getPriceLinePath () {
      let path = 'M0,75'
      for (let i = 1; i <= 12; i++) {
        const y = 75 - Math.sin(i * 0.5) * 20
        path += ` L${i * 30 + 15},${y}`
      }
      return path
    },

    // 获取指标标签
    getMetricLabel (index) {
      const labels = ['AI置信度', '市场情绪', '技术指标', '风险评估']
      return labels[index] || '指标'
    },

    // 获取指标值
    getMetricValue (index) {
      const base = [85, 72, 68, 45]
      const variation = Math.sin(Date.now() / 1000 + index) * 5
      return Math.round(base[index] + variation) + '%'
    },

    // 获取指标条样式
    getMetricBarStyle (index) {
      const base = [85, 72, 68, 45]
      const variation = Math.sin(Date.now() / 1000 + index) * 5
      const width = Math.max(0, Math.min(100, base[index] + variation))
      return {
        width: `${width}%`,
        transition: 'width 0.5s ease'
      }
    },

    // 获取 agent 状态
    getAgentStatus (agentIndex) {
      // 如果有分析结果且不在分析中（历史记录查看模式），所有 agent 都显示为完成
      if (this.hasAnalysisResults && !this.analyzing) {
        return 'completed'
      }

      // Use local agentStatusMap for simulation status
      if (this.agentStatusMap[agentIndex]) {
        return this.agentStatusMap[agentIndex]
      }

      // Default to waiting
      return 'waiting'
    },

    // 处理 agent 点击
    handleAgentClick (agentIndex) {
      if (!this.hasResult && !this.hasAnalysisResults) return
      this.selectedAgentIndex = agentIndex
    },

    // 获取 agent 对应的结果
    getAgentResult (agentIndex) {
      if (agentIndex === null || agentIndex < 0 || agentIndex >= this.agents.length) {
        return null
      }
      const resultKey = this.agents[agentIndex].resultKey
      if (!resultKey || !this.analysisResults) {
        return null
      }

      // 处理特殊的 resultKey（debate_bull, debate_bear, debate_research）
      if (resultKey === 'debate_bull') {
        return this.analysisResults.debate?.bull || null
      } else if (resultKey === 'debate_bear') {
        return this.analysisResults.debate?.bear || null
      } else if (resultKey === 'debate_research') {
        return this.analysisResults.debate?.research_decision || null
      }

      return this.analysisResults[resultKey]
    },

    // 格式化报告
    formatReport (report) {
      if (!report) return ''
      // 简单的 Markdown 格式化
      return report
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>')
    },

    // 获取维度名称
    getDimensionName (dimension) {
      return this.$t(`dashboard.analysis.dimension.${dimension}`) || dimension
    },

    // 获取交易计划参数标签
    getTradingPlanLabel (key) {
      const translationKey = `dashboard.analysis.tradingPlan.${key}`
      const translated = this.$t(translationKey)
      // 如果翻译键不存在，VueI18n 会返回翻译键本身，此时返回原始key
      // 如果翻译成功，返回翻译后的文本
      if (translated && translated !== translationKey) {
        return translated
      }
      // 如果翻译失败，返回格式化的key（将下划线替换为空格并首字母大写）
      return key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
    },

    // 获取分数样式类
    getScoreClass (score) {
      if (score >= 80) return 'score-high'
      if (score >= 60) return 'score-medium'
      return 'score-low'
    },

    // 获取分数状态
    getScoreStatus (score) {
      if (score >= 80) return 'success'
      if (score >= 60) return 'active'
      return 'exception'
    },

    // 获取指标样式类
    getIndicatorClass (value) {
      if (typeof value === 'string') {
        if (value.includes('买入') || value.includes('向上')) return 'indicator-positive'
        if (value.includes('卖出') || value.includes('向下')) return 'indicator-negative'
      }
      return 'indicator-neutral'
    },

    // 获取情绪状态
    getSentimentStatus (score) {
      if (score >= 70) return 'success'
      if (score >= 50) return 'active'
      return 'exception'
    },

    // 获取风险样式类
    getRiskClass (value) {
      if (typeof value === 'string') {
        if (value.includes('低')) return 'risk-low'
        if (value.includes('中')) return 'risk-medium'
      }
      return 'risk-high'
    },

    // 选择第一个有结果的 agent（优先选择投资总监，显示在最上面）
    selectFirstAvailableAgent () {
      // 优先选择投资总监（数组最后一个，反转后显示在最上面）
      const investmentDirectorIndex = this.agents.length - 1
      if (this.getAgentResult(investmentDirectorIndex)) {
        this.selectedAgentIndex = investmentDirectorIndex
        return
      }

      // 如果没有，选择其他有结果的 agent
      for (let i = 0; i < this.agents.length; i++) {
        if (this.getAgentResult(i)) {
          this.selectedAgentIndex = i
          return
        }
      }
    }
  }
}
</script>

<style lang="less" scoped>
/* Cyberpunk Theme Variables */
// @bg-dark: var(--bg-color);
@bg-panel: var(--panel-bg);
@text-main: var(--text-color);
@neon-blue: var(--neon-main);
@neon-purple: #722ed1;
@neon-green: #52c41a;
@neon-red: #f5222d;
@border-color: var(--border-color);

.metaverse-container {
  position: relative;
  width: 100%;
  height: calc(100vh - 64px);
  max-height: calc(100vh - 64px);
  // background-color: @bg-dark;
  color: @text-main;
  overflow: hidden;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  display: flex;
  flex-direction: column;
  /* 尝试修复可能的父容器 padding 问题 */
  margin: -24px;
  width: calc(100% + 48px);
}

/* Background Effects */
.bg-grid {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background-image: linear-gradient(@border-color 1px, transparent 1px),
  linear-gradient(90deg, @border-color 1px, transparent 1px);
  background-size: 50px 50px;
  opacity: 0.1;
  z-index: 0;
  pointer-events: none;
  perspective: 1000px;
  transform-style: preserve-3d;
}
.bg-glow {
  position: absolute;
  // top: 50%; left: 50%;
  // width: 1000px; height: 1000px;
  background: radial-gradient(circle, rgba(0, 229, 255, 0.03) 0%, transparent 70%);
  transform: translate(-50%, -50%);
  z-index: 0;
  pointer-events: none;
}
.bg-particles {
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  overflow: hidden;
  z-index: 0;
  .particle {
    position: absolute;
    width: 2px; height: 2px;
    background: var(--particle-color);
    opacity: 0.3;
    animation: floatUp linear infinite;
  }
}

/* Header Info (Moved inside Center Stage) */
.center-header-info {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  z-index: 10;
  background: rgba(0, 0, 0, 0.2); /* Semi-transparent */
  backdrop-filter: blur(5px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);

  .logo-section {
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 2px;
    display: flex;
    align-items: center;
    gap: 10px;
    .logo-icon { font-size: 24px; filter: drop-shadow(0 0 5px @neon-blue); }
    .highlight { color: @neon-blue; text-shadow: 0 0 10px @neon-blue; }
  }

  .status-bar {
    display: flex;
    gap: 30px;
    font-size: 12px;

    .status-item {
      display: flex;
      gap: 10px;
      align-items: center;
      .label { color: #888; font-weight: 600; }
      .value { color: @neon-blue; font-weight: bold; font-family: 'Orbitron', sans-serif; }
      .value.online { color: @neon-green; text-shadow: 0 0 5px @neon-green; }
    }
  }
}

/* Empty State Styles */
.empty-state {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;

    .empty-content {
    width: 100%;
    text-align: center;
    padding: 20px;

    .empty-icon {
      margin-bottom: 16px;
      .icon-circle {
        width: 80px;
        height: 80px;
        margin: 0 auto;
        background: var(--empty-hover-bg);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 2px solid var(--empty-hover-border);
        box-shadow: 0 0 30px var(--empty-hover-border);
        .anticon {
          font-size: 32px;
          color: var(--icon-color);
        }
      }
    }

    p {
      color: @text-main;
      opacity: 0.7;
      font-size: 13px;
      margin-bottom: 20px;
    }

    .empty-features-wrapper {
      width: 100%;
      overflow: hidden;
      position: relative;
      max-width: 100%;
    }

    .empty-features {
      width: 100%;
      overflow: hidden;
      position: relative;
    }

    .features-track {
      display: flex;
      gap: 12px;
      padding: 10px 0;
      width: max-content;
      animation: scroll-left 20s linear infinite;
      will-change: transform;

      .feature-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
        padding: 8px 16px;
        background: var(--empty-bg);
        border: 1px solid var(--empty-border);
        border-radius: 8px;
        transition: all 0.3s;
        min-width: 100px;
        flex-shrink: 0;
        white-space: nowrap;

        &:hover {
          background: var(--empty-hover-bg);
          border-color: var(--primary-color);
          transform: translateY(-2px);
          box-shadow: 0 4px 12px var(--empty-hover-border);

          .anticon { color: var(--primary-color); }
          span { color: var(--text-color); }
        }

        .anticon {
          font-size: 20px;
          color: var(--icon-color);
          opacity: 0.8;
          transition: color 0.3s;
        }

        span {
          font-size: 12px;
          color: var(--text-color);
          opacity: 0.6;
          font-weight: 500;
          transition: color 0.3s;
        }
      }
    }
  }
}
/* Header (Removed but keeping reference just in case of revert, commented out in template) */
.meta-header {
  height: 60px;
  border-bottom: 1px solid @border-color;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  z-index: 10;
  background: var(--header-bg);
  backdrop-filter: blur(10px);
  box-shadow: 0 5px 20px var(--shadow-color);
  position: sticky; /* 防止滚动时消失 */
  top: 0;
  width: 100%;

  .logo-section {
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 2px;
    display: flex;
    align-items: center;
    gap: 10px;
    .logo-icon { font-size: 24px; filter: drop-shadow(0 0 5px @neon-blue); }
    .highlight { color: @neon-blue; text-shadow: 0 0 10px @neon-blue; }
  }

  .status-bar {
    display: flex;
    gap: 30px;
    font-size: 12px;

    .status-item {
      display: flex;
      gap: 10px;
      align-items: center;
      .label { color: #666; font-weight: 600; }
      .value { color: @neon-blue; font-weight: bold; font-family: 'Orbitron', sans-serif; }
      .value.online { color: @neon-green; text-shadow: 0 0 5px @neon-green; }
    }
  }
}

/* Main Layout */
.main-console {
  flex: 1;
  display: flex;
  padding: 20px;
  gap: 20px;
  z-index: 10;
  overflow: hidden;
  min-height: 0;
  max-height: 100%;

  // 当有结果时，调整布局
  &.has-result {
    .left-panel {
      width: 300px; // 稍微缩小左侧面板
    }
    .middle-panel {
      flex: 1; // 中间面板占据剩余所有空间
      margin-right: 0; // 移除右边距，因为右侧面板已隐藏
    }
    .right-panel {
      display: none; // 隐藏右侧面板
    }
  }
}

.left-panel {
  width: 320px;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  min-height: 0;
  max-height: 100%;
  overflow: hidden;
}

.middle-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  max-height: 100%;
  overflow: hidden;
  margin: 0 20px;
  background: var(--panel-bg);
  border: 1px solid @border-color;
  border-radius: 4px;
  padding: 20px;
  transition: all 0.3s ease; // 添加过渡效果

  .result-content {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    /* 隐藏滚动条但保持滚动功能 */
    scrollbar-width: none; /* Firefox */
    -ms-overflow-style: none; /* IE and Edge */
    &::-webkit-scrollbar {
      display: none; /* Chrome, Safari, Opera */
    }
  }

  .agent-result-panel {
    width: 100%;
    height: 100%;
  }

  .analysis-panel {
    width: 100%;
  }

  .select-hint,
  .no-result-hint {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    min-height: 300px;
  }

  // 复用父组件的样式
  .overview-content,
  .fundamental-content,
  .technical-content,
  .news-content,
  .sentiment-content,
  .risk-content,
  .debate-content,
  .decision-content {
    width: 100%;

    // 适配 ant-card 主题色
    ::v-deep .ant-card {
      background: var(--panel-bg);
      border-color: var(--border-color);
      color: var(--text-color);

      .ant-card-head {
        border-bottom-color: var(--border-color);

        .ant-card-head-title {
          color: var(--text-color);
          font-weight: 600;
        }
      }

      .ant-card-body {
        color: var(--text-color);
      }
    }

    // 适配 ant-collapse 主题色
    ::v-deep .ant-collapse {
      background: var(--panel-bg);
      border-color: var(--border-color);

      .ant-collapse-item {
        border-color: var(--border-color);

        .ant-collapse-header {
          color: var(--text-color);
          background: var(--panel-bg);

          &:hover {
            background: var(--summary-bg, var(--panel-bg));
          }

          .ant-collapse-arrow {
            color: var(--text-color);
          }
        }

        &.ant-collapse-item-active {
          .ant-collapse-header {
            color: var(--primary-color);
          }
        }

        .ant-collapse-content {
          background: var(--panel-bg);
          border-top-color: var(--border-color);

          .ant-collapse-content-box {
            color: var(--text-color);
          }
        }
      }
    }
  }

  .score-cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 16px;
  }

  .score-card {
    text-align: center;
    background: var(--panel-bg);
    border-color: var(--border-color);

    &.score-high { border-left: 4px solid #52c41a; }
    &.score-medium { border-left: 4px solid #faad14; }
    &.score-low { border-left: 4px solid #f5222d; }
  }

  .score-content {
    .score-value {
      font-size: 32px;
      font-weight: bold;
      margin-bottom: 8px;
    }
    .score-label {
      font-size: 14px;
      color: var(--text-color);
      opacity: 0.6;
    }
  }

  .dimension-scores,
  .financial-metrics,
  .technical-indicators,
  .news-list,
  .sentiment-scores,
  .risk-metrics {
    display: flex;
    flex-direction: column;
    gap: 12px;

    // 进度条：强制显示百分比，隐藏图标
    ::v-deep .ant-progress {
      width: 80% !important;
      .ant-progress-text {
        color: var(--text-color);
      }

      &.ant-progress-status-success .anticon-check-circle,
      &.ant-progress-status-exception .anticon-close-circle {
        display: none !important;
      }
      &.ant-progress-status-success .ant-progress-text,
      &.ant-progress-status-exception .ant-progress-text {
        display: inline-block !important;
        color: var(--text-color) !important;
      }
    }
  }

  .dimension-score-item,
  .metric-item,
  .indicator-item,
  .news-item,
  .sentiment-item,
  .risk-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid var(--border-color);
  }

  .dimension-name,
  .metric-label,
  .indicator-label,
  .sentiment-source,
  .risk-label {
    font-weight: 500;
    color: var(--text-color);
  }

  .metric-value,
  .indicator-value,
  .risk-value {
    font-weight: bold;
    &.indicator-positive { color: #52c41a; }
    &.indicator-negative { color: #f5222d; }
    &.indicator-neutral { color: var(--text-color); opacity: 0.6; }
    &.risk-low { color: #52c41a; }
    &.risk-medium { color: #faad14; }
    &.risk-high { color: #f5222d; }
  }

  .news-item {
    flex-direction: column;
    align-items: flex-start;
    h4 {
      margin: 0 0 8px 0;
      font-size: 16px;
    }
    p {
      margin: 0 0 8px 0;
      color: var(--text-color);
      opacity: 0.6;
    }
    .news-meta {
      display: flex;
      gap: 16px;
      font-size: 12px;
      color: var(--text-color);
      opacity: 0.6;
    }
  }

  .analysis-report {
    line-height: 1.8;
    color: var(--text-color);
  }

  .key-points {
    margin-bottom: 12px;
    h4 {
      margin-bottom: 8px;
      font-size: 14px;
    }
    ul {
      margin: 0;
      padding-left: 20px;
      li {
        margin-bottom: 4px;
      }
    }
  }
}

.agents-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0;
  overflow: hidden;
  position: relative;
  min-height: 0;

  /* 隐藏滚动条但保持滚动功能 */
  &.custom-scroll {
    overflow-y: auto;
    overflow-x: hidden;
    /* 隐藏滚动条 */
    scrollbar-width: none; /* Firefox */
    -ms-overflow-style: none; /* IE and Edge */
    &::-webkit-scrollbar {
      display: none; /* Chrome, Safari, Opera */
    }
  }
  overscroll-behavior: contain; /* 防止滚动链 */

  .panel-title {
    width: 98%;
    position: sticky;
    top: 0;
    z-index: 10;
    background: var(--terminal-header-bg);
    color: var(--text-color);
    opacity: 0.7;
    font-size: 12px;
    letter-spacing: 2px;
    margin-bottom: 12px;
    padding: 12px 5px;
    border-left: 2px solid var(--primary-color);
    border-bottom: 1px solid var(--border-color);
  }

  .agents-list {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 12px;
    overflow-y: auto;
    overflow-x: visible; // 允许横向溢出，以便选中时能看到边框
    padding-right: 15px; // 增加右边距，为选中时的偏移留出空间
    /* 隐藏滚动条但保持滚动功能 */
    scrollbar-width: none; /* Firefox */
    -ms-overflow-style: none; /* IE and Edge */
    &::-webkit-scrollbar {
      display: none; /* Chrome, Safari, Opera */
    }
  }

  .agent-card {
    background: @bg-panel;
    border: 1px solid @border-color;
    padding: 10px 15px;
    border-radius: 4px; /* 恢复为圆角边框 */
    /* 移除 clip-path */
    /* clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px); */
    display: flex;
    align-items: center;
    gap: 15px;
    transition: all 0.3s;
    position: relative;
    opacity: 0.6;
    min-height: 80px;

    &.active {
      border-color: var(--primary-color);
      box-shadow: 0 0 15px var(--empty-hover-bg);
      background: linear-gradient(90deg, var(--empty-hover-bg) 0%, transparent 100%);
      opacity: 1;
      transform: translateX(10px);
      margin-right: 0px; // 补偿向右偏移，保持右边距
      z-index: 50; // 增加z-index，确保边框可见
      position: relative; // 确保z-index生效
    }

    &.selected {
      border-color: var(--primary-color);
      box-shadow: 0 0 20px var(--empty-hover-bg);
      background: linear-gradient(90deg, var(--empty-hover-bg) 0%, transparent 100%);
      opacity: 1;
      transform: translateX(10px);
      border-width: 2px;
      margin-right: 0px; // 补偿向右偏移，保持右边距
      z-index: 100; // 增加z-index，确保边框可见
      position: relative; // 确保z-index生效
    }

    &.completed {
      border-color: @neon-green;
      opacity: 0.8;
      .agent-name { color: @neon-green; }
    }

    .agent-avatar {
      position: relative;
      width: 48px; height: 48px;
      img { width: 100%; height: 100%; border-radius: 50%; background: #2a2e39; }

      .pulse-ring {
        position: absolute;
        top: -4px; left: -4px; right: -4px; bottom: -4px;
        border: 2px solid var(--primary-color);
        border-radius: 50%;
        animation: pulse 1.5s infinite;
      }
    }

    .agent-info {
      flex: 1;
      .agent-name { font-weight: bold; font-size: 14px; letter-spacing: 0.5px; color: var(--text-color); }
      .agent-role { font-size: 10px; color: var(--text-color); opacity: 0.6; text-transform: uppercase; margin-bottom: 4px; }
      .agent-status {
        font-size: 11px;
        .typing { color: var(--primary-color); animation: blink 1s infinite; }
        .done { color: @neon-green; }
        .wait { color: var(--text-color); opacity: 0.4; }
      }
    }
  }
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow: hidden;
  min-width: 0;
}

.center-stage {
  flex: 2; // 核心区域占比更大
  background: var(--center-bg);
  border: 1px solid @border-color;
  border-radius: 4px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  min-height: 300px;

  /* Idle State */
  .idle-interface {
    text-align: center;
    width: 70%;
    z-index: 2;

    .welcome-title {
      font-size: 32px;
      margin-bottom: 50px;
      letter-spacing: 6px;
      color: var(--text-color);
      text-transform: uppercase;
      text-shadow: 0 0 10px var(--primary-color), 0 0 20px var(--primary-color);
      animation: glow 3s ease-in-out infinite alternate;
    }

    .input-group {
      display: flex;
      gap: 15px;
      margin-bottom: 50px;
      justify-content: center;
      max-width: 600px;
      margin-left: auto;
      margin-right: auto;

      .cyber-select {
        flex: 1;
        ::v-deep .ant-select-selection {
          background: var(--input-bg);
          border: 1px solid var(--primary-color);
          height: 50px;
          color: var(--text-color);
          display: flex;
          align-items: center;
          font-family: monospace;
          font-size: 18px;
          border-radius: 0;
        }
        ::v-deep .ant-select-arrow { color: var(--primary-color); }
      }

      .cyber-button {
        background: var(--primary-color);
        color: #000;
        border: none;
        padding: 0 40px;
        font-weight: 800;
        font-family: 'Orbitron', monospace;
        cursor: pointer;
        position: relative;
        overflow: hidden;
        transition: all 0.3s;
        clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);

        &:hover {
          background: #fff;
          box-shadow: 0 0 30px var(--empty-hover-border);
          transform: translateY(-2px);
        }

        &:disabled {
          background: #333;
          color: #666;
          cursor: not-allowed;
          box-shadow: none;
          transform: none;
        }
      }
    }

    .recent-searches {
       text-align: center;
       .section-label { color: #666; font-size: 12px; margin-bottom: 15px; letter-spacing: 2px; }
       .tags {
         display: flex;
         gap: 12px;
         justify-content: center;
         .cyber-tag {
           background: rgba(255,255,255,0.05);
           border: 1px solid var(--border-color);
           padding: 6px 14px;
           font-size: 12px;
           cursor: pointer;
           transition: all 0.2s;
           color: var(--text-color);
           &:hover { border-color: var(--primary-color); color: var(--primary-color); box-shadow: 0 0 10px var(--empty-hover-bg); }
         }
       }
    }
  }

  /* Running State */
  .running-interface {
    width: 100%; height: 100%;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;

    .vis-container {
      width: 100%;
      height: 100%;
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto;
      overflow: hidden;
      background: radial-gradient(circle at center, rgba(24, 144, 255, 0.03) 0%, transparent 70%);

      // 科技背景层
      .tech-background {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 1;
        overflow: hidden;

        // 像素风格猫
        .pixel-cat {
          position: absolute;
          bottom: 15%;
          left: 10%;
          width: 80px;
          height: 80px;
          z-index: 2;
          opacity: 0.5;
          animation: catFloat 4s ease-in-out infinite;
          image-rendering: pixelated;
          image-rendering: -moz-crisp-edges;
          image-rendering: crisp-edges;

          .cat-body {
            position: absolute;
            bottom: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 50px;
            height: 40px;
            background: #ffa500;
            border: 2px solid #ff8c00;
            box-shadow:
              inset -4px 0 0 #ff8c00,
              inset 4px 0 0 #ff8c00,
              0 0 10px rgba(255, 165, 0, 0.4);
          }

          .cat-head {
            position: absolute;
            top: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 50px;
            height: 50px;
            background: #ffa500;
            border: 2px solid #ff8c00;
            border-radius: 50% 50% 45% 45%;
            box-shadow: 0 0 10px rgba(255, 165, 0, 0.4);
          }

          .cat-ear {
            position: absolute;
            top: -8px;
            width: 16px;
            height: 16px;
            background: #ffa500;
            border: 2px solid #ff8c00;
            clip-path: polygon(50% 0%, 0% 100%, 100% 100%);
            box-shadow: 0 0 8px rgba(255, 165, 0, 0.4);

            &.cat-ear-left {
              left: 8px;
            }

            &.cat-ear-right {
              right: 8px;
            }
          }

          .cat-eye {
            position: absolute;
            top: 18px;
            width: 6px;
            height: 8px;
            background: #00ffff;
            border: 1px solid #00cccc;
            border-radius: 50%;
            box-shadow: 0 0 8px #00ffff, 0 0 12px #00ffff;
            animation: catBlink 3s ease-in-out infinite;

            &.cat-eye-left {
              left: 14px;
            }

            &.cat-eye-right {
              right: 14px;
            }
          }

          .cat-nose {
            position: absolute;
            top: 28px;
            left: 50%;
            transform: translateX(-50%);
            width: 6px;
            height: 4px;
            background: #ff69b4;
            clip-path: polygon(50% 100%, 0% 0%, 100% 0%);
          }

          .cat-mouth {
            position: absolute;
            top: 32px;
            left: 50%;
            transform: translateX(-50%);
            width: 12px;
            height: 8px;
            border: 1px solid #ff8c00;
            border-top: none;
            border-radius: 0 0 50% 50%;
          }

          .cat-tail {
            position: absolute;
            bottom: 20px;
            right: -15px;
            width: 20px;
            height: 40px;
            background: #ffa500;
            border: 2px solid #ff8c00;
            border-radius: 50% 0 0 50%;
            transform: rotate(-20deg);
            transform-origin: bottom left;
            animation: catTail 2s ease-in-out infinite;
            box-shadow: 0 0 8px rgba(255, 165, 0, 0.4);
          }
        }

        // 神经网络
        .neural-network {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          z-index: 1;
          opacity: 0.3;

          .neural-path {
            stroke-dasharray: 5, 5;
            animation: neuralPulse 3s ease-in-out infinite;
          }

          .neural-node {
            filter: drop-shadow(0 0 4px var(--primary-color));
            animation: nodePulse 2s ease-in-out infinite;
          }
        }

        // 矩阵雨效果
        .matrix-rain {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          z-index: 1;
          opacity: 0.2;
          overflow: hidden;
          pointer-events: none;

          .matrix-column {
            position: absolute;
            top: -100%;
            width: 3px;
            height: 200%;
            background: linear-gradient(to bottom,
              transparent 0%,
              rgba(24, 144, 255, 0.1) 20%,
              rgba(24, 144, 255, 0.6) 50%,
              rgba(24, 144, 255, 0.1) 80%,
              transparent 100%);
            animation: matrixFall linear infinite;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            color: var(--primary-color);
            text-shadow: 0 0 8px var(--primary-color);
            white-space: nowrap;

            &::before {
              content: attr(data-char);
              position: absolute;
              top: 0;
              left: 0;
              width: 100%;
              color: var(--primary-color);
              text-align: center;
              animation: matrixText 0.5s linear infinite;
            }
          }
        }
      }

      // 核心内容
      .holo-core {
        z-index: 10;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        position: relative;

        .core-icon {
          width: 120px;
          height: 120px;
          margin-bottom: 20px;
          position: relative;

          .ai-hologram {
            width: 100%;
            height: 100%;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;

            .hologram-ring {
              position: absolute;
              border: 2px solid var(--primary-color);
              border-radius: 50%;
              opacity: 0.6;
              animation: ringRotate 4s linear infinite;

              &.ring-1 {
                width: 100%;
                height: 100%;
                box-shadow: 0 0 20px rgba(24, 144, 255, 0.5);
              }

              &.ring-2 {
                width: 80%;
                height: 80%;
                animation-duration: 3s;
                animation-direction: reverse;
                box-shadow: 0 0 15px rgba(114, 46, 209, 0.4);
              }

              &.ring-3 {
                width: 60%;
                height: 60%;
                animation-duration: 2s;
                box-shadow: 0 0 10px rgba(24, 144, 255, 0.3);
              }
            }

            .core-avatar {
              width: 80px;
              height: 80px;
              border-radius: 50%;
              position: relative;
              z-index: 2;
              filter: drop-shadow(0 0 15px rgba(24, 144, 255, 0.8));
              border: 2px solid var(--primary-color);
            }

            .hologram-scan-line {
              position: absolute;
              top: 0;
              left: 0;
              width: 100%;
              height: 2px;
              background: linear-gradient(90deg, transparent, var(--primary-color), transparent);
              z-index: 3;
              animation: scanLine 2s linear infinite;
              box-shadow: 0 0 10px var(--primary-color);
            }
          }
        }

        .holo-content {
          .current-task-label {
            color: var(--primary-color);
            font-size: 12px;
            margin-bottom: 8px;
            letter-spacing: 4px;
            text-transform: uppercase;
            font-family: 'Orbitron', monospace;
            text-shadow: 0 0 10px var(--primary-color);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;

            .label-prefix {
              color: #00ffff;
              text-shadow: 0 0 8px #00ffff;
              animation: blink 1.5s ease-in-out infinite;
            }
          }
          .current-agent-name {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 12px;
            color: var(--text-color);
            text-shadow: 0 0 15px rgba(24, 144, 255, 0.8);
            font-family: 'Orbitron', monospace;
          }
          .current-task-detail {
            font-size: 14px;
            color: var(--text-color);
            opacity: 0.7;
            max-width: 350px;
            height: 40px;
            overflow: hidden;
            font-family: monospace;
          }
        }
      }

      // 金融数据可视化
      .financial-visualization {
        position: absolute;
        bottom: 15%;
        left: 5%;
        width: 90%;
        height: 25%;
        z-index: 3;
        opacity: 0.7;

        .candlestick-chart {
          width: 100%;
          height: 100%;

          .chart-grid {
            opacity: 0.2;
          }

          .candlestick {
            animation: candlePulse 2s ease-in-out infinite;
          }

          .price-line {
            filter: drop-shadow(0 0 3px rgba(24, 144, 255, 0.8));
            stroke-dasharray: 10, 5;
            animation: priceLineFlow 3s ease-in-out infinite;
          }
        }
      }

      // AI分析指标
      .ai-metrics {
        position: absolute;
        top: 10%;
        right: 5%;
        width: 200px;
        z-index: 4;
        display: flex;
        flex-direction: column;
        gap: 12px;

        .metric-card {
          background: rgba(24, 144, 255, 0.05);
          border: 1px solid rgba(24, 144, 255, 0.3);
          border-radius: 4px;
          padding: 10px;
          backdrop-filter: blur(5px);

          .metric-label {
            font-size: 10px;
            color: var(--text-color);
            opacity: 0.7;
            margin-bottom: 4px;
            font-family: monospace;
            text-transform: uppercase;
            letter-spacing: 1px;
          }

          .metric-value {
            font-size: 18px;
            font-weight: bold;
            color: var(--primary-color);
            margin-bottom: 6px;
            font-family: 'Orbitron', monospace;
            text-shadow: 0 0 8px var(--primary-color);
          }

          .metric-bar {
            width: 100%;
            height: 4px;
            background: rgba(24, 144, 255, 0.1);
            border-radius: 2px;
            overflow: hidden;

            .metric-fill {
              height: 100%;
              background: linear-gradient(90deg, var(--primary-color), rgba(114, 46, 209, 0.8));
              border-radius: 2px;
              box-shadow: 0 0 8px var(--primary-color);
              transition: width 0.5s ease;
            }
          }
        }
      }

      // 全息投影边框
      .hologram-border {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 6;
        pointer-events: none;

        .border-corner {
          position: absolute;
          width: 50px;
          height: 50px;

          .corner-line {
            position: absolute;
            background: var(--primary-color);
            box-shadow: 0 0 10px var(--primary-color);

            &.corner-line-h {
              width: 30px;
              height: 2px;
            }

            &.corner-line-v {
              width: 2px;
              height: 30px;
            }
          }

          &.corner-tl {
            top: 15px;
            left: 15px;

            .corner-line-h {
              top: 0;
              left: 0;
            }

            .corner-line-v {
              top: 0;
              left: 0;
            }
          }

          &.corner-tr {
            top: 15px;
            right: 15px;

            .corner-line-h {
              top: 0;
              right: 0;
            }

            .corner-line-v {
              top: 0;
              right: 0;
            }
          }

          &.corner-bl {
            bottom: 15px;
            left: 15px;

            .corner-line-h {
              bottom: 0;
              left: 0;
            }

            .corner-line-v {
              bottom: 0;
              left: 0;
            }
          }

          &.corner-br {
            bottom: 15px;
            right: 15px;

            .corner-line-h {
              bottom: 0;
              right: 0;
            }

            .corner-line-v {
              bottom: 0;
              right: 0;
            }
          }
        }
      }
    }
  }

  /* Result State */
  .result-interface {
    width: 100%; height: 100%;
    padding: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 5;

    .result-card {
      width: 700px;
      background: var(--card-bg);
      border: 1px solid @neon-green;
      box-shadow: 0 0 50px rgba(82, 196, 26, 0.15);
      padding: 40px;
      clip-path: polygon(20px 0, 100% 0, 100% calc(100% - 20px), calc(100% - 20px) 100%, 0 100%, 0 20px);

      .result-header {
        border-bottom: 1px solid #333;
        padding-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        .asset-title { font-size: 28px; color: @text-main; font-weight: bold; letter-spacing: 1px; }
        .timestamp { font-size: 12px; color: #666; font-family: monospace; }
      }

      .result-body {
        padding: 30px 0;
        text-align: center;

        .signal-box {
          border: 2px solid #555;
          padding: 20px 40px;
          display: inline-block;
          margin-bottom: 30px;
          min-width: 250px;
          position: relative;

          &::before { content: ''; position: absolute; top: -5px; left: -5px; width: 10px; height: 10px; border-top: 2px solid currentColor; border-left: 2px solid currentColor; }
          &::after { content: ''; position: absolute; bottom: -5px; right: -5px; width: 10px; height: 10px; border-bottom: 2px solid currentColor; border-right: 2px solid currentColor; }

          .signal-label { font-size: 12px; color: #888; letter-spacing: 4px; margin-bottom: 10px; }
          .signal-value { font-size: 48px; font-weight: 900; margin-bottom: 5px; font-family: 'Orbitron', sans-serif; }
          .confidence { font-size: 14px; font-weight: bold; opacity: 0.8; }

          &.signal-buy {
            border-color: @neon-green; color: @neon-green;
            background: rgba(82, 196, 26, 0.05);
            box-shadow: 0 0 30px rgba(82, 196, 26, 0.1);
          }
          &.signal-sell {
            border-color: @neon-red; color: @neon-red;
            background: rgba(245, 34, 45, 0.05);
            box-shadow: 0 0 30px rgba(245, 34, 45, 0.1);
          }
          &.signal-neutral {
            border-color: @neon-purple; color: @neon-purple;
          }
        }

        .summary-text {
          text-align: left;
          font-size: 14px;
          line-height: 1.8;
          color: var(--text-color);
          background: var(--summary-bg);
          padding: 20px;
          border-left: 4px solid var(--primary-color);
          margin-top: 10px;
        }
      }

      .result-actions {
        display: flex;
        gap: 20px;
        justify-content: center;
        margin-top: 10px;

        .cyber-button {
          background: transparent;
          border: 1px solid var(--primary-color);
          color: var(--primary-color);
          padding: 12px 30px;
          cursor: pointer;
          font-family: monospace;
          font-weight: bold;
          transition: all 0.3s;
          &:hover { background: var(--primary-color); color: #000; box-shadow: 0 0 15px var(--empty-hover-border); }

          &.secondary {
             border-color: var(--text-color);
             color: var(--text-color);
             opacity: 0.6;
             &:hover { border-color: var(--text-color); color: var(--text-color); background: transparent; opacity: 1; }
          }
        }
      }
    }
  }
}

.terminal-panel {
  width: 100%;
  flex: 1; // 占据右侧剩余空间（底部）
  min-height: 200px;
  display: flex;
  flex-direction: column;
  border-left: none;
  border-top: 1px solid @border-color;
  background: var(--terminal-bg);
  backdrop-filter: blur(5px);

  .terminal-header {
    padding: 12px 15px;
    font-size: 12px;
    background: var(--terminal-header-bg);
    border-bottom: 1px solid var(--border-color);
    color: var(--text-color);
    opacity: 0.7;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .terminal-window {
    flex: 1;
    overflow-y: auto;
    padding: 15px;
    font-family: 'Consolas', monospace;
    font-size: 12px;

    /* Scrollbar */
    &::-webkit-scrollbar { width: 6px; }
    &::-webkit-scrollbar-track { background: #111; }
    &::-webkit-scrollbar-thumb { background: #333; }

    .log-line {
      margin-bottom: 8px;
      line-height: 1.4;
      display: flex;
      .log-time { color: @text-main; opacity: 0.6; margin-right: 10px; min-width: 60px; }
      .log-source { font-weight: bold; margin-right: 8px; color: @text-main; }
      .log-msg { color: @text-main; word-break: break-word; }
    }

    .cursor-blink {
      animation: blink 1s infinite;
      color: var(--primary-color);
    }
  }
}

/* Animations */
@keyframes scroll-left {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(-50%);
  }
}

@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@keyframes scan {
  0% { top: -40px; opacity: 0; }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% { top: 100%; opacity: 0; }
}
@keyframes pulse { 0% { transform: scale(1); opacity: 1; } 100% { transform: scale(1.5); opacity: 0; } }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
@keyframes floatUp { 0% { transform: translateY(100vh); opacity: 0; } 50% { opacity: 1; } 100% { transform: translateY(-100px); opacity: 0; } }
@keyframes glow { from { text-shadow: 0 0 10px var(--primary-color); } to { text-shadow: 0 0 20px var(--primary-color), 0 0 40px var(--primary-color); } }

// 金融科技特效动画
@keyframes gridMove {
  0% {
    background-position: 0 0;
  }
  100% {
    background-position: 40px 40px;
  }
}

@keyframes particleFloat {
  0%, 100% {
    transform: translate(0, 0) scale(1);
    opacity: 0.3;
  }
  50% {
    transform: translate(20px, -30px) scale(1.5);
    opacity: 1;
  }
}

@keyframes hologramPulse {
  0%, 100% {
    box-shadow:
      0 0 20px rgba(24, 144, 255, 0.5),
      inset 0 0 20px rgba(24, 144, 255, 0.2);
  }
  50% {
    box-shadow:
      0 0 40px rgba(24, 144, 255, 0.8),
      inset 0 0 30px rgba(24, 144, 255, 0.4);
  }
}

@keyframes scanLine {
  0% {
    top: 0;
    opacity: 0;
  }
  10% {
    opacity: 1;
  }
  90% {
    opacity: 1;
  }
  100% {
    top: 100%;
    opacity: 0;
  }
}

@keyframes chartPulse {
  0%, 100% {
    opacity: 0.6;
  }
  50% {
    opacity: 1;
  }
}

@keyframes pointPulse {
  0%, 100% {
    r: 3;
    opacity: 0.8;
  }
  50% {
    r: 5;
    opacity: 1;
  }
}

@keyframes dataFlow {
  0% {
    transform: translateY(0);
    opacity: 0;
  }
  10% {
    opacity: 1;
  }
  90% {
    opacity: 1;
  }
  100% {
    transform: translateY(-200px);
    opacity: 0;
  }
}

// 新特效动画
@keyframes catFloat {
  0%, 100% {
    transform: translateY(0) translateX(0);
  }
  50% {
    transform: translateY(-10px) translateX(5px);
  }
}

@keyframes catBlink {
  0%, 90%, 100% {
    height: 8px;
  }
  95% {
    height: 2px;
  }
}

@keyframes catTail {
  0%, 100% {
    transform: rotate(-20deg);
  }
  50% {
    transform: rotate(-30deg);
  }
}

@keyframes neuralPulse {
  0%, 100% {
    stroke-dashoffset: 0;
    opacity: 0.4;
  }
  50% {
    stroke-dashoffset: -10;
    opacity: 0.8;
  }
}

@keyframes nodePulse {
  0%, 100% {
    r: 4;
    opacity: 0.8;
  }
  50% {
    r: 6;
    opacity: 1;
  }
}

@keyframes matrixFall {
  0% {
    top: -100%;
  }
  100% {
    top: 100%;
  }
}

@keyframes matrixText {
  0% {
    opacity: 0.3;
    transform: translateY(0);
  }
  50% {
    opacity: 1;
  }
  100% {
    opacity: 0.3;
    transform: translateY(20px);
  }
}

@keyframes ringRotate {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

@keyframes candlePulse {
  0%, 100% {
    opacity: 0.8;
  }
  50% {
    opacity: 1;
  }
}

@keyframes priceLineFlow {
  0%, 100% {
    stroke-dashoffset: 0;
  }
  50% {
    stroke-dashoffset: -20;
  }
}

/* ant-btn-link 样式跟随主题色 */
::v-deep .ant-btn-link,
.ant-btn-link {
  color: var(--primary-color) !important;
  border-color: transparent;
  background: transparent;
  transition: all 0.3s;

  &:hover,
  &:focus {
    color: var(--link-hover-color) !important;
    border-color: transparent;
    background: transparent;
  }

  &:active {
    color: var(--primary-color) !important;
    border-color: transparent;
    background: transparent;
  }

  &[disabled] {
    color: var(--text-color) !important;
    opacity: 0.4;
    cursor: not-allowed;
  }
}

/* Responsive */
@media (max-width: 1400px) {
  .left-panel { width: 300px; }
}

@media (max-width: 768px) {
  .metaverse-container {
    height: auto;
    overflow-y: auto;
    overflow-x: hidden;
    margin: -12px;
    width: calc(100% + 24px);
    min-height: calc(100vh - 64px);
  }

  .main-console {
    flex-direction: column;
    height: auto;
    padding: 12px;
    gap: 12px;

    &.has-result {
      .left-panel {
        width: 100%;
        height: 200px;
        min-height: 160px;
        max-height: 200px;
      }
      .middle-panel {
        flex: 1;
        margin: 0;
        min-height: 400px;
      }
    }
  }

  .left-panel {
    width: 100%;
    height: 200px;
    min-height: 160px;
    max-height: 200px;
    overflow: hidden;
  }

  .agents-panel {
    width: 100%;
    height: 100%;
    position: relative;
    overflow: hidden;

    .panel-title {
      font-size: 11px;
      padding: 10px 8px;
      text-align: left!important;
    }

    /* 添加左右渐变遮罩，提示可以滑动 */
    &::before,
    &::after {
      content: '';
      position: absolute;
      top: 0;
      bottom: 0;
      width: 30px;
      pointer-events: none;
      z-index: 2;
      transition: opacity 0.3s;
    }

    &::before {
      left: 0;
      background: linear-gradient(to right, var(--panel-bg), transparent);
    }

    &::after {
      right: 0;
      background: linear-gradient(to left, var(--panel-bg), transparent);
    }

    .agents-list {
      display: flex;
      flex-direction: row;
      overflow-x: auto;
      overflow-y: hidden;
      gap: 12px;
      padding: 8px 12px;
      scroll-snap-type: x mandatory;
      -webkit-overflow-scrolling: touch;
      scrollbar-width: thin;
      scrollbar-color: var(--primary-color) transparent;
      position: relative;
      overscroll-behavior-x: contain;
      overscroll-behavior-y: none;

      &::-webkit-scrollbar {
        height: 4px;
      }

      &::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.1);
        border-radius: 2px;
      }

      &::-webkit-scrollbar-thumb {
        background: var(--primary-color);
        border-radius: 2px;
        opacity: 0.6;

        &:hover {
          opacity: 1;
        }
      }
    }

    .agent-card {
      flex: 0 0 auto;
      width: 140px;
      min-width: 140px;
      padding: 12px;
      min-height: 120px;
      gap: 8px;
      flex-direction: column;
      align-items: center;
      text-align: center;
      scroll-snap-align: center;
      border-radius: 8px;

      &.active,
      &.selected {
        transform: scale(1.05);
        margin-right: 0;
        border-width: 2px;
        box-shadow: 0 4px 12px rgba(24, 144, 255, 0.3);
      }

      .agent-avatar {
        width: 50px;
        height: 50px;
        flex-shrink: 0;
        margin-bottom: 4px;
      }

      .agent-info {
        flex: 1;
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;

        .agent-name {
          font-size: 12px;
          font-weight: 600;
          white-space: normal;
          overflow: visible;
          text-overflow: unset;
          line-height: 1.3;
          margin-bottom: 4px;
          word-break: break-word;
        }

        .agent-role {
          font-size: 9px;
          margin-bottom: 6px;
          opacity: 0.7;
          line-height: 1.2;
        }

        .agent-status {
          font-size: 10px;
          margin-top: auto;
        }
      }

      .agent-visual {
        position: absolute;
        top: 8px;
        right: 8px;
        flex-shrink: 0;

        .anticon {
          font-size: 16px;
        }
      }
    }
  }

  .middle-panel {
    width: 100%;
    margin: 0;
    padding: 12px;
    min-height: 400px;

    .result-content {
      padding: 0;
    }

    .score-cards {
      grid-template-columns: 1fr;
      gap: 12px;
      margin-bottom: 12px;
    }

    .score-card {
      .score-content {
        .score-value {
          font-size: 28px;
        }
        .score-label {
          font-size: 12px;
        }
      }
    }

    ::v-deep .ant-card {
      margin-bottom: 12px;

      .ant-card-head {
        padding: 12px 16px;

        .ant-card-head-title {
          font-size: 14px;
        }
      }

      .ant-card-body {
        padding: 12px 16px;
      }
    }

    .dimension-scores,
    .financial-metrics,
    .technical-indicators,
    .news-list,
    .sentiment-scores,
    .risk-metrics {
      gap: 10px;
    }

    .dimension-score-item,
    .metric-item,
    .indicator-item,
    .news-item,
    .sentiment-item,
    .risk-item {
      padding: 6px 0;
      flex-wrap: wrap;

      .dimension-name,
      .metric-label,
      .indicator-label,
      .sentiment-source,
      .risk-label {
        font-size: 12px;
        width: 100%;
        margin-bottom: 4px;
      }

      ::v-deep .ant-progress {
        width: 100% !important;
      }
    }

    .news-item {
      h4 {
        font-size: 14px;
      }
      p {
        font-size: 12px;
      }
      .news-meta {
        font-size: 11px;
        gap: 12px;
      }
    }

    .analysis-report {
      font-size: 13px;
      line-height: 1.6;
    }

    .key-points {
      h4 {
        font-size: 13px;
      }
      ul {
        padding-left: 18px;
        li {
          font-size: 12px;
          margin-bottom: 3px;
        }
      }
    }

    .decision-content {
      ::v-deep .ant-card {
        .ant-card-body {
          > div {
            flex-direction: column !important;
            gap: 12px !important;
          }
        }
      }
    }

    .final-decision-header {
      div {
        font-size: 28px !important;
      }
    }
  }

  .right-panel {
    width: 100%;
    min-height: 400px;
  }

  .center-stage {
    min-height: 300px;
    padding: 12px;

    .idle-interface {
      width: 100%;
      padding: 20px 12px;

      .empty-content {
        padding: 12px;

        .empty-icon {
          margin-bottom: 12px;

          .icon-circle {
            width: 60px;
            height: 60px;

            .anticon {
              font-size: 24px;
            }
          }
        }

        p {
          font-size: 12px;
          margin-bottom: 16px;
        }

        .empty-features-wrapper {
          .features-track {
            gap: 8px;
            padding: 8px 0;

            .feature-item {
              padding: 6px 12px;
              min-width: 80px;

              .anticon {
                font-size: 16px;
              }

              span {
                font-size: 11px;
              }
            }
          }
        }
      }
    }

    .running-interface {
      .vis-container {
        width: 100%;
        height: 100%;
        min-height: 300px;

        .holo-core {
          .core-icon {
            width: 80px;
            height: 80px;
            margin-bottom: 12px;

            .core-avatar {
              width: 60px;
              height: 60px;
            }
          }

          .holo-content {
            .current-task-label {
              font-size: 10px;
              letter-spacing: 2px;
            }

            .current-agent-name {
              font-size: 18px;
              margin-bottom: 8px;
            }

            .current-task-detail {
              font-size: 12px;
              max-width: 90%;
              height: 32px;
            }
          }
        }

        .financial-visualization {
          bottom: 10%;
          left: 2%;
          width: 96%;
          height: 20%;
        }
      }
    }
  }

  .terminal-panel {
    width: 100%;
    height: 200px;
    min-height: 200px;
    max-height: 250px;

    .terminal-header {
      padding: 10px 12px;
      font-size: 11px;
    }

    .terminal-window {
      padding: 12px;
      font-size: 11px;

      .log-line {
        margin-bottom: 6px;
        flex-wrap: wrap;

        .log-time {
          font-size: 10px;
          min-width: 50px;
        }

        .log-source {
          font-size: 10px;
        }

        .log-msg {
          font-size: 10px;
          width: 100%;
          margin-top: 2px;
        }
      }
    }
  }

  .result-interface {
    padding: 20px 12px;

    .result-card {
      width: 100%;
      padding: 16px;

      .result-header {
        padding-bottom: 12px;

        .asset-title {
          font-size: 20px;
        }

        .timestamp {
          font-size: 11px;
        }
      }

      .result-body {
        padding: 20px 0;

        .summary-text {
          font-size: 12px;
          padding: 12px;
        }
      }
    }
  }
}

</style>

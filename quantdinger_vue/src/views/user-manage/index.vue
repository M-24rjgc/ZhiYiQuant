<template>
  <div class="user-manage-page" :class="{ 'theme-dark': isDarkTheme }">
    <div class="page-header">
      <h2 class="page-title">
        <a-icon type="team" />
        <span>{{ $t('userManage.title') || 'User Management' }}</span>
      </h2>
      <p class="page-desc">{{ $t('userManage.description') || 'Manage system users, roles and permissions' }}</p>
    </div>

    <!-- Tabs -->
    <a-tabs v-model="activeTab" @change="handleTabChange" class="manage-tabs">
      <!-- Tab 1: User Management -->
      <a-tab-pane key="users" :tab="$t('userManage.tabUsers') || 'User Management'">
        <!-- Toolbar -->
        <div class="toolbar">
          <div class="toolbar-left">
            <a-button type="primary" @click="showCreateModal">
              <a-icon type="user-add" />
              {{ $t('userManage.createUser') || 'Create User' }}
            </a-button>
            <a-button @click="loadUsers">
              <a-icon type="reload" />
              {{ $t('common.refresh') || 'Refresh' }}
            </a-button>
          </div>
          <div class="toolbar-right">
            <a-input-search
              v-model="searchKeyword"
              :placeholder="$t('userManage.searchPlaceholder') || 'Search by username/email'"
              style="width: 280px"
              allowClear
              @search="handleSearch"
              @pressEnter="handleSearch"
            />
          </div>
        </div>

        <!-- User Table -->
        <a-card :bordered="false" class="user-table-card">
          <a-table
            :columns="columns"
            :dataSource="users"
            :loading="loading"
            :pagination="pagination"
            :rowKey="record => record.id"
            @change="handleTableChange"
          >
            <!-- Status Column -->
            <template slot="status" slot-scope="text">
              <a-tag :color="text === 'active' ? 'green' : 'red'">
                {{ text === 'active' ? ($t('userManage.active') || 'Active') : ($t('userManage.disabled') || 'Disabled') }}
              </a-tag>
            </template>

            <!-- Role Column -->
            <template slot="role" slot-scope="text">
              <a-tag :color="getRoleColor(text)">
                {{ getRoleLabel(text) }}
              </a-tag>
            </template>

            <!-- Last Login Column -->
            <template slot="last_login_at" slot-scope="text">
              <span v-if="text">{{ formatTime(text) }}</span>
              <span v-else class="text-muted">{{ $t('userManage.neverLogin') || 'Never' }}</span>
            </template>

            <!-- Credits Column -->
            <template slot="credits" slot-scope="text">
              <span class="credits-value">{{ formatCredits(text) }}</span>
            </template>

            <!-- VIP Column -->
            <template slot="vip_expires_at" slot-scope="text">
              <template v-if="text && isVipActive(text)">
                <a-tag color="gold">
                  <a-icon type="crown" />
                  {{ formatDate(text) }}
                </a-tag>
              </template>
              <span v-else class="text-muted">-</span>
            </template>

            <!-- Actions Column -->
            <template slot="action" slot-scope="text, record">
              <a-space>
                <a-tooltip :title="$t('common.edit') || 'Edit'">
                  <a-button type="link" size="small" @click="showEditModal(record)">
                    <a-icon type="edit" />
                  </a-button>
                </a-tooltip>
                <a-tooltip :title="$t('userManage.adjustCredits') || 'Adjust Credits'">
                  <a-button type="link" size="small" @click="showCreditsModal(record)">
                    <a-icon type="wallet" style="color: #722ed1" />
                  </a-button>
                </a-tooltip>
                <a-tooltip :title="$t('userManage.setVip') || 'Set VIP'">
                  <a-button type="link" size="small" @click="showVipModal(record)">
                    <a-icon type="crown" style="color: #faad14" />
                  </a-button>
                </a-tooltip>
                <a-tooltip :title="$t('userManage.resetPassword') || 'Reset Password'">
                  <a-button type="link" size="small" @click="showResetPasswordModal(record)">
                    <a-icon type="key" />
                  </a-button>
                </a-tooltip>
                <a-tooltip :title="$t('common.delete') || 'Delete'">
                  <a-popconfirm
                    :title="$t('userManage.confirmDelete') || 'Are you sure to delete this user?'"
                    @confirm="handleDelete(record.id)"
                  >
                    <a-button type="link" size="small" :disabled="record.id === currentUserId">
                      <a-icon type="delete" style="color: #ff4d4f" />
                    </a-button>
                  </a-popconfirm>
                </a-tooltip>
              </a-space>
            </template>
          </a-table>
        </a-card>
      </a-tab-pane>

      <!-- Tab 2: System Strategy Overview -->
      <a-tab-pane key="strategies" :tab="$t('systemOverview.tabTitle') || 'System Overview'">
        <!-- Summary Cards -->
        <div class="summary-cards" v-if="strategySummary">
          <div class="summary-card">
            <div class="summary-icon" style="background: linear-gradient(135deg, #667eea, #764ba2)">
              <a-icon type="fund" />
            </div>
            <div class="summary-info">
              <div class="summary-value">{{ strategySummary.total_strategies || 0 }}</div>
              <div class="summary-label">{{ $t('systemOverview.totalStrategies') || 'Total Strategies' }}</div>
            </div>
          </div>
          <div class="summary-card">
            <div class="summary-icon" style="background: linear-gradient(135deg, #11998e, #38ef7d)">
              <a-icon type="play-circle" />
            </div>
            <div class="summary-info">
              <div class="summary-value">{{ strategySummary.running_strategies || 0 }}</div>
              <div class="summary-label">{{ $t('systemOverview.runningStrategies') || 'Running' }}</div>
            </div>
          </div>
          <div class="summary-card">
            <div class="summary-icon" style="background: linear-gradient(135deg, #f093fb, #f5576c)">
              <a-icon type="dollar" />
            </div>
            <div class="summary-info">
              <div class="summary-value">{{ formatNumber(strategySummary.total_capital) }}</div>
              <div class="summary-label">{{ $t('systemOverview.totalCapital') || 'Total Capital' }}</div>
            </div>
          </div>
          <div class="summary-card">
            <div class="summary-icon" :style="{ background: (strategySummary.total_pnl || 0) >= 0 ? 'linear-gradient(135deg, #11998e, #38ef7d)' : 'linear-gradient(135deg, #ff416c, #ff4b2b)' }">
              <a-icon type="rise" />
            </div>
            <div class="summary-info">
              <div class="summary-value" :class="(strategySummary.total_pnl || 0) >= 0 ? 'text-profit' : 'text-loss'">
                {{ formatPnl(strategySummary.total_pnl) }}
                <span class="roi-badge">{{ strategySummary.total_roi || 0 }}%</span>
              </div>
              <div class="summary-label">{{ $t('systemOverview.totalPnl') || 'Total PnL' }}</div>
            </div>
          </div>
        </div>

        <!-- Strategy Toolbar -->
        <div class="toolbar">
          <div class="toolbar-left">
            <a-button @click="loadSystemStrategies">
              <a-icon type="reload" />
              {{ $t('common.refresh') || 'Refresh' }}
            </a-button>
            <a-select v-model="strategyStatusFilter" style="width: 140px" @change="handleStrategyFilterChange">
              <a-select-option value="all">{{ $t('systemOverview.filterAll') || 'All Status' }}</a-select-option>
              <a-select-option value="running">{{ $t('systemOverview.filterRunning') || 'Running' }}</a-select-option>
              <a-select-option value="stopped">{{ $t('systemOverview.filterStopped') || 'Stopped' }}</a-select-option>
            </a-select>
          </div>
          <div class="toolbar-right">
            <a-input-search
              v-model="strategySearchKeyword"
              :placeholder="$t('systemOverview.searchPlaceholder') || 'Search strategy/symbol/user'"
              style="width: 280px"
              allowClear
              @search="handleStrategySearch"
              @pressEnter="handleStrategySearch"
            />
          </div>
        </div>

        <!-- Strategy Table -->
        <a-card :bordered="false" class="user-table-card">
          <a-table
            :columns="strategyColumns"
            :dataSource="systemStrategies"
            :loading="strategyLoading"
            :pagination="strategyPagination"
            :rowKey="record => record.id"
            :scroll="{ x: 1600 }"
            @change="handleStrategyTableChange"
          >
            <!-- Strategy Status -->
            <template slot="strategyStatus" slot-scope="text">
              <span class="status-cell">
                <span class="status-dot" :class="text === 'running' ? 'dot-running' : 'dot-stopped'" />
                <span :class="text === 'running' ? 'status-running' : 'status-stopped'">
                  {{ text === 'running' ? ($t('systemOverview.running') || 'Running') : ($t('systemOverview.stopped') || 'Stopped') }}
                </span>
              </span>
            </template>

            <!-- User Column -->
            <template slot="userInfo" slot-scope="text, record">
              <a-tooltip :title="(record.nickname || record.username || '-')">
                <span class="user-cell">
                  <a-avatar size="small" :style="{ backgroundColor: getUserColor(record.user_id), fontSize: '11px', marginRight: '6px' }">
                    {{ (record.nickname || record.username || '?').charAt(0).toUpperCase() }}
                  </a-avatar>
                  <span class="user-name">{{ truncate(record.nickname || record.username || '-', 8) }}</span>
                </span>
              </a-tooltip>
            </template>

            <!-- Symbol Column -->
            <template slot="symbolInfo" slot-scope="text, record">
              <div>
                <span class="symbol-text">{{ record.symbol || '-' }}</span>
                <a-tag v-if="record.cs_strategy_type === 'cross_sectional'" color="purple" size="small" style="margin-left: 4px">CS</a-tag>
              </div>
              <div v-if="record.cs_strategy_type === 'cross_sectional' && record.symbol_list && record.symbol_list.length" class="symbol-count text-muted">
                {{ record.symbol_list.length }} {{ $t('systemOverview.symbols') || 'symbols' }}
              </div>
            </template>

            <!-- Capital Column -->
            <template slot="capitalInfo" slot-scope="text">
              <span>{{ formatNumber(text) }}</span>
            </template>

            <!-- PnL Column -->
            <template slot="pnlInfo" slot-scope="text, record">
              <div :class="record.total_pnl >= 0 ? 'text-profit' : 'text-loss'">
                <span class="pnl-value">{{ formatPnl(record.total_pnl) }}</span>
                <span class="roi-text">({{ record.roi >= 0 ? '+' : '' }}{{ record.roi }}%)</span>
              </div>
              <div class="pnl-detail text-muted">
                <span>{{ $t('systemOverview.realized') || 'Real' }}: {{ formatPnl(record.total_realized_pnl) }}</span>
                <span style="margin-left: 8px">{{ $t('systemOverview.unrealized') || 'Unreal' }}: {{ formatPnl(record.total_unrealized_pnl) }}</span>
              </div>
            </template>

            <!-- Positions Column -->
            <template slot="positionInfo" slot-scope="text, record">
              <a-badge :count="record.position_count" :numberStyle="{ backgroundColor: record.position_count > 0 ? '#52c41a' : '#d9d9d9' }" />
            </template>

            <!-- Trades Column -->
            <template slot="tradeInfo" slot-scope="text">
              <span>{{ text || 0 }}</span>
            </template>

            <!-- Indicator Column -->
            <template slot="indicatorInfo" slot-scope="text">
              <a-tooltip v-if="text" :title="text">
                <span class="indicator-name">{{ truncate(text, 16) }}</span>
              </a-tooltip>
              <span v-else class="text-muted">-</span>
            </template>

            <!-- Exchange Column -->
            <template slot="exchangeInfo" slot-scope="text">
              <span v-if="text" class="exchange-name">{{ text }}</span>
              <span v-else class="text-muted">-</span>
            </template>

            <!-- Timeframe Column -->
            <template slot="timeframeInfo" slot-scope="text">
              <a-tag v-if="text" size="small">{{ text }}</a-tag>
              <span v-else class="text-muted">-</span>
            </template>

            <!-- Leverage Column -->
            <template slot="leverageInfo" slot-scope="text">
              <span v-if="text > 1" style="color: #fa8c16; font-weight: 600">{{ text }}x</span>
              <span v-else>{{ text || 1 }}x</span>
            </template>

            <!-- Created At Column -->
            <template slot="createdAtInfo" slot-scope="text">
              <span v-if="text">{{ formatTime(text) }}</span>
              <span v-else class="text-muted">-</span>
            </template>
          </a-table>
        </a-card>
      </a-tab-pane>
    </a-tabs>

    <!-- Create/Edit User Modal -->
    <a-modal
      v-model="modalVisible"
      :title="isEdit ? ($t('userManage.editUser') || 'Edit User') : ($t('userManage.createUser') || 'Create User')"
      :confirmLoading="modalLoading"
      @ok="handleModalOk"
      @cancel="handleModalCancel"
    >
      <a-form :form="form" layout="vertical">
        <a-form-item :label="$t('userManage.username') || 'Username'">
          <a-input
            v-decorator="['username', {
              rules: [{ required: !isEdit, message: $t('userManage.usernameRequired') || 'Please enter username' }]
            }]"
            :disabled="isEdit"
            :placeholder="$t('userManage.usernamePlaceholder') || 'Enter username'"
          >
            <a-icon slot="prefix" type="user" />
          </a-input>
        </a-form-item>

        <a-form-item v-if="!isEdit" :label="$t('userManage.password') || 'Password'">
          <a-input-password
            v-decorator="['password', {
              rules: [
                { required: true, message: $t('userManage.passwordRequired') || 'Please enter password' },
                { min: 6, message: $t('userManage.passwordMin') || 'Password must be at least 6 characters' }
              ]
            }]"
            :placeholder="$t('userManage.passwordPlaceholder') || 'Enter password (min 6 characters)'"
          >
            <a-icon slot="prefix" type="lock" />
          </a-input-password>
        </a-form-item>

        <a-form-item :label="$t('userManage.nickname') || 'Nickname'">
          <a-input
            v-decorator="['nickname']"
            :placeholder="$t('userManage.nicknamePlaceholder') || 'Enter nickname'"
          >
            <a-icon slot="prefix" type="smile" />
          </a-input>
        </a-form-item>

        <a-form-item :label="$t('userManage.email') || 'Email'">
          <a-input
            v-decorator="['email', {
              rules: [{ type: 'email', message: $t('userManage.emailInvalid') || 'Invalid email format' }]
            }]"
            :placeholder="$t('userManage.emailPlaceholder') || 'Enter email'"
          >
            <a-icon slot="prefix" type="mail" />
          </a-input>
        </a-form-item>

        <a-form-item :label="$t('userManage.role') || 'Role'">
          <a-select
            v-decorator="['role', { initialValue: 'user' }]"
            :placeholder="$t('userManage.rolePlaceholder') || 'Select role'"
          >
            <a-select-option v-for="role in roles" :key="role.id" :value="role.id">
              {{ getRoleLabel(role.id) }}
            </a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item v-if="isEdit" :label="$t('userManage.status') || 'Status'">
          <a-select
            v-decorator="['status', { initialValue: 'active' }]"
            :placeholder="$t('userManage.statusPlaceholder') || 'Select status'"
          >
            <a-select-option value="active">{{ $t('userManage.active') || 'Active' }}</a-select-option>
            <a-select-option value="disabled">{{ $t('userManage.disabled') || 'Disabled' }}</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- Reset Password Modal -->
    <a-modal
      v-model="resetPasswordVisible"
      :title="$t('userManage.resetPassword') || 'Reset Password'"
      :confirmLoading="resetPasswordLoading"
      @ok="handleResetPassword"
    >
      <a-form :form="resetPasswordForm" layout="vertical">
        <a-alert
          :message="$t('userManage.resetPasswordWarning') || 'This will reset the user\'s password'"
          type="warning"
          showIcon
          style="margin-bottom: 16px"
        />
        <a-form-item :label="$t('userManage.newPassword') || 'New Password'">
          <a-input-password
            v-decorator="['new_password', {
              rules: [
                { required: true, message: $t('userManage.passwordRequired') || 'Please enter new password' },
                { min: 6, message: $t('userManage.passwordMin') || 'Password must be at least 6 characters' }
              ]
            }]"
            :placeholder="$t('userManage.newPasswordPlaceholder') || 'Enter new password'"
          >
            <a-icon slot="prefix" type="lock" />
          </a-input-password>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- Adjust Credits Modal -->
    <a-modal
      v-model="creditsModalVisible"
      :title="($t('userManage.adjustCredits') || 'Adjust Credits') + (creditsEditingUser ? ` - ${creditsEditingUser.username}` : '')"
      :confirmLoading="creditsLoading"
      @ok="handleSetCredits"
    >
      <a-form layout="vertical">
        <div class="current-credits-info" v-if="creditsEditingUser">
          <span class="label">{{ $t('userManage.currentCredits') || 'Current Credits' }}:</span>
          <span class="value">{{ formatCredits(creditsEditingUser.credits) }}</span>
        </div>
        <a-form-item :label="$t('userManage.newCredits') || 'New Credits'">
          <a-input-number
            v-model="newCredits"
            :min="0"
            :precision="2"
            style="width: 100%"
            :placeholder="$t('userManage.enterCredits') || 'Enter new credits amount'"
          />
        </a-form-item>
        <a-form-item :label="$t('userManage.remark') || 'Remark'">
          <a-input
            v-model="creditsRemark"
            :placeholder="$t('userManage.remarkPlaceholder') || 'Optional remark'"
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- Set VIP Modal -->
    <a-modal
      v-model="vipModalVisible"
      :title="($t('userManage.setVip') || 'Set VIP') + (vipEditingUser ? ` - ${vipEditingUser.username}` : '')"
      :confirmLoading="vipLoading"
      @ok="handleSetVip"
    >
      <a-form layout="vertical">
        <div class="current-vip-info" v-if="vipEditingUser && vipEditingUser.vip_expires_at">
          <span class="label">{{ $t('userManage.currentVip') || 'Current VIP' }}:</span>
          <span class="value" :class="isVipActive(vipEditingUser.vip_expires_at) ? 'active' : 'expired'">
            {{ isVipActive(vipEditingUser.vip_expires_at)
              ? ($t('userManage.vipActive') || 'Active') + ` (${formatDate(vipEditingUser.vip_expires_at)})`
              : ($t('userManage.vipExpired') || 'Expired') }}
          </span>
        </div>
        <a-form-item :label="$t('userManage.vipDays') || 'VIP Days'">
          <a-select v-model="vipDays" style="width: 100%">
            <a-select-option :value="0">{{ $t('userManage.cancelVip') || 'Cancel VIP' }}</a-select-option>
            <a-select-option :value="7">7 {{ $t('userManage.days') || 'days' }}</a-select-option>
            <a-select-option :value="30">30 {{ $t('userManage.days') || 'days' }}</a-select-option>
            <a-select-option :value="90">90 {{ $t('userManage.days') || 'days' }}</a-select-option>
            <a-select-option :value="180">180 {{ $t('userManage.days') || 'days' }}</a-select-option>
            <a-select-option :value="365">365 {{ $t('userManage.days') || 'days' }}</a-select-option>
            <a-select-option :value="-1">{{ $t('userManage.customDate') || 'Custom Date' }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item v-if="vipDays === -1" :label="$t('userManage.vipExpiresAt') || 'VIP Expires At'">
          <a-date-picker
            v-model="vipCustomDate"
            showTime
            format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
          />
        </a-form-item>
        <a-form-item :label="$t('userManage.remark') || 'Remark'">
          <a-input
            v-model="vipRemark"
            :placeholder="$t('userManage.remarkPlaceholder') || 'Optional remark'"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script>
import { getUserList, createUser, updateUser, deleteUser, resetUserPassword, getRoles, setUserCredits, setUserVip, getSystemStrategies } from '@/api/user'
import { baseMixin } from '@/store/app-mixin'
import { mapGetters } from 'vuex'

export default {
  name: 'UserManage',
  mixins: [baseMixin],
  data () {
    return {
      activeTab: 'users',
      loading: false,
      users: [],
      roles: [],
      searchKeyword: '',
      pagination: {
        current: 1,
        pageSize: 10,
        total: 0
      },
      // Create/Edit Modal
      modalVisible: false,
      modalLoading: false,
      isEdit: false,
      editingUser: null,
      // Reset Password Modal
      resetPasswordVisible: false,
      resetPasswordLoading: false,
      resetPasswordUserId: null,
      // Credits Modal
      creditsModalVisible: false,
      creditsLoading: false,
      creditsEditingUser: null,
      newCredits: 0,
      creditsRemark: '',
      // VIP Modal
      vipModalVisible: false,
      vipLoading: false,
      vipEditingUser: null,
      vipDays: 30,
      vipCustomDate: null,
      vipRemark: '',
      // System Strategy Overview
      strategyLoading: false,
      systemStrategies: [],
      strategySummary: null,
      strategyStatusFilter: 'all',
      strategySearchKeyword: '',
      strategyPagination: {
        current: 1,
        pageSize: 20,
        total: 0
      },
      strategiesLoaded: false
    }
  },
  computed: {
    ...mapGetters(['userInfo']),
    isDarkTheme () {
      return this.navTheme === 'dark' || this.navTheme === 'realdark'
    },
    currentUserId () {
      return this.userInfo?.id
    },
    columns () {
      return [
        {
          title: 'ID',
          dataIndex: 'id',
          width: 60
        },
        {
          title: this.$t('userManage.username') || 'Username',
          dataIndex: 'username',
          width: 120
        },
        {
          title: this.$t('userManage.nickname') || 'Nickname',
          dataIndex: 'nickname',
          width: 100
        },
        {
          title: this.$t('userManage.email') || 'Email',
          dataIndex: 'email',
          width: 180
        },
        {
          title: this.$t('userManage.role') || 'Role',
          dataIndex: 'role',
          width: 90,
          scopedSlots: { customRender: 'role' }
        },
        {
          title: this.$t('userManage.credits') || 'Credits',
          dataIndex: 'credits',
          width: 100,
          scopedSlots: { customRender: 'credits' }
        },
        {
          title: 'VIP',
          dataIndex: 'vip_expires_at',
          width: 120,
          scopedSlots: { customRender: 'vip_expires_at' }
        },
        {
          title: this.$t('userManage.status') || 'Status',
          dataIndex: 'status',
          width: 90,
          scopedSlots: { customRender: 'status' }
        },
        {
          title: this.$t('userManage.lastLogin') || 'Last Login',
          dataIndex: 'last_login_at',
          width: 150,
          scopedSlots: { customRender: 'last_login_at' }
        },
        {
          title: this.$t('common.actions') || 'Actions',
          dataIndex: 'action',
          width: 180,
          scopedSlots: { customRender: 'action' }
        }
      ]
    },
    strategyColumns () {
      return [
        {
          title: 'ID',
          dataIndex: 'id',
          width: 60,
          fixed: 'left'
        },
        {
          title: this.$t('systemOverview.colUser') || 'User',
          dataIndex: 'username',
          width: 110,
          fixed: 'left',
          scopedSlots: { customRender: 'userInfo' }
        },
        {
          title: this.$t('systemOverview.colStrategy') || 'Strategy',
          dataIndex: 'strategy_name',
          width: 160,
          ellipsis: true
        },
        {
          title: this.$t('systemOverview.colStatus') || 'Status',
          dataIndex: 'status',
          width: 100,
          scopedSlots: { customRender: 'strategyStatus' }
        },
        {
          title: this.$t('systemOverview.colSymbol') || 'Symbol',
          dataIndex: 'symbol',
          width: 140,
          scopedSlots: { customRender: 'symbolInfo' }
        },
        {
          title: this.$t('systemOverview.colCapital') || 'Capital',
          dataIndex: 'initial_capital',
          width: 110,
          scopedSlots: { customRender: 'capitalInfo' }
        },
        {
          title: this.$t('systemOverview.colPnl') || 'PnL / ROI',
          dataIndex: 'total_pnl',
          width: 200,
          scopedSlots: { customRender: 'pnlInfo' }
        },
        {
          title: this.$t('systemOverview.colPositions') || 'Pos',
          dataIndex: 'position_count',
          width: 70,
          align: 'center',
          scopedSlots: { customRender: 'positionInfo' }
        },
        {
          title: this.$t('systemOverview.colTrades') || 'Trades',
          dataIndex: 'trade_count',
          width: 80,
          align: 'center',
          scopedSlots: { customRender: 'tradeInfo' }
        },
        {
          title: this.$t('systemOverview.colIndicator') || 'Indicator',
          dataIndex: 'indicator_name',
          width: 130,
          scopedSlots: { customRender: 'indicatorInfo' }
        },
        {
          title: this.$t('systemOverview.colExchange') || 'Exchange',
          dataIndex: 'exchange_name',
          width: 100,
          scopedSlots: { customRender: 'exchangeInfo' }
        },
        {
          title: this.$t('systemOverview.colTimeframe') || 'TF',
          dataIndex: 'timeframe',
          width: 70,
          align: 'center',
          scopedSlots: { customRender: 'timeframeInfo' }
        },
        {
          title: this.$t('systemOverview.colLeverage') || 'Lev',
          dataIndex: 'leverage',
          width: 70,
          align: 'center',
          scopedSlots: { customRender: 'leverageInfo' }
        },
        {
          title: this.$t('systemOverview.colCreatedAt') || 'Created',
          dataIndex: 'created_at',
          width: 150,
          scopedSlots: { customRender: 'createdAtInfo' }
        }
      ]
    }
  },
  beforeCreate () {
    this.form = this.$form.createForm(this)
    this.resetPasswordForm = this.$form.createForm(this, { name: 'resetPassword' })
  },
  mounted () {
    this.loadUsers()
    this.loadRoles()
  },
  methods: {
    handleTabChange (key) {
      if (key === 'strategies' && !this.strategiesLoaded) {
        this.loadSystemStrategies()
      }
    },

    // ==================== System Strategy Overview ====================
    async loadSystemStrategies () {
      this.strategyLoading = true
      try {
        const res = await getSystemStrategies({
          page: this.strategyPagination.current,
          page_size: this.strategyPagination.pageSize,
          status: this.strategyStatusFilter === 'all' ? '' : this.strategyStatusFilter,
          search: this.strategySearchKeyword || ''
        })
        if (res.code === 1) {
          this.systemStrategies = res.data.items || []
          this.strategyPagination.total = res.data.total || 0
          this.strategySummary = res.data.summary || {}
          this.strategiesLoaded = true
        } else {
          this.$message.error(res.msg || 'Failed to load strategies')
        }
      } catch (error) {
        console.error('Failed to load system strategies:', error)
        this.$message.error('Failed to load system strategies')
      } finally {
        this.strategyLoading = false
      }
    },

    handleStrategySearch () {
      this.strategyPagination.current = 1
      this.loadSystemStrategies()
    },

    handleStrategyFilterChange () {
      this.strategyPagination.current = 1
      this.loadSystemStrategies()
    },

    handleStrategyTableChange (pagination) {
      this.strategyPagination.current = pagination.current
      this.strategyPagination.pageSize = pagination.pageSize
      this.loadSystemStrategies()
    },

    getUserColor (userId) {
      const colors = ['#1890ff', '#722ed1', '#13c2c2', '#fa8c16', '#eb2f96', '#52c41a', '#2f54eb', '#faad14']
      return colors[(userId || 0) % colors.length]
    },

    formatNumber (num) {
      if (!num && num !== 0) return '0'
      return Number(num).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
    },

    formatPnl (pnl) {
      if (!pnl && pnl !== 0) return '0'
      const val = Number(pnl)
      const prefix = val >= 0 ? '+' : ''
      return prefix + val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
    },

    truncate (str, maxLen) {
      if (!str) return ''
      return str.length > maxLen ? str.substring(0, maxLen) + '...' : str
    },

    // ==================== User Management ====================
    async loadUsers () {
      this.loading = true
      try {
        const res = await getUserList({
          page: this.pagination.current,
          page_size: this.pagination.pageSize,
          search: this.searchKeyword || ''
        })
        if (res.code === 1) {
          this.users = res.data.items || []
          this.pagination.total = res.data.total || 0
        } else {
          this.$message.error(res.msg || 'Failed to load users')
        }
      } catch (error) {
        this.$message.error('Failed to load users')
      } finally {
        this.loading = false
      }
    },

    handleSearch () {
      this.pagination.current = 1
      this.loadUsers()
    },

    async loadRoles () {
      try {
        const res = await getRoles()
        if (res.code === 1) {
          this.roles = res.data.roles || []
        }
      } catch (error) {
        console.error('Failed to load roles:', error)
      }
    },

    handleTableChange (pagination) {
      this.pagination.current = pagination.current
      this.pagination.pageSize = pagination.pageSize
      this.loadUsers()
    },

    showCreateModal () {
      this.isEdit = false
      this.editingUser = null
      this.modalVisible = true
      this.$nextTick(() => {
        this.form.resetFields()
      })
    },

    showEditModal (record) {
      this.isEdit = true
      this.editingUser = record
      this.modalVisible = true
      this.$nextTick(() => {
        this.form.setFieldsValue({
          username: record.username,
          nickname: record.nickname,
          email: record.email,
          role: record.role,
          status: record.status
        })
      })
    },

    handleModalCancel () {
      this.modalVisible = false
      this.form.resetFields()
    },

    handleModalOk () {
      this.form.validateFields(async (err, values) => {
        if (err) return

        this.modalLoading = true
        try {
          let res
          if (this.isEdit) {
            res = await updateUser(this.editingUser.id, {
              nickname: values.nickname,
              email: values.email,
              role: values.role,
              status: values.status
            })
          } else {
            res = await createUser(values)
          }

          if (res.code === 1) {
            this.$message.success(res.msg || 'Success')
            this.modalVisible = false
            this.form.resetFields()
            this.loadUsers()
          } else {
            this.$message.error(res.msg || 'Operation failed')
          }
        } catch (error) {
          this.$message.error('Operation failed')
        } finally {
          this.modalLoading = false
        }
      })
    },

    async handleDelete (id) {
      try {
        const res = await deleteUser(id)
        if (res.code === 1) {
          this.$message.success(res.msg || 'User deleted')
          this.loadUsers()
        } else {
          this.$message.error(res.msg || 'Delete failed')
        }
      } catch (error) {
        this.$message.error('Delete failed')
      }
    },

    showResetPasswordModal (record) {
      this.resetPasswordUserId = record.id
      this.resetPasswordVisible = true
      this.$nextTick(() => {
        this.resetPasswordForm.resetFields()
      })
    },

    handleResetPassword () {
      this.resetPasswordForm.validateFields(async (err, values) => {
        if (err) return

        this.resetPasswordLoading = true
        try {
          const res = await resetUserPassword({
            user_id: this.resetPasswordUserId,
            new_password: values.new_password
          })
          if (res.code === 1) {
            this.$message.success(res.msg || 'Password reset successfully')
            this.resetPasswordVisible = false
            this.resetPasswordForm.resetFields()
          } else {
            this.$message.error(res.msg || 'Reset failed')
          }
        } catch (error) {
          this.$message.error('Reset failed')
        } finally {
          this.resetPasswordLoading = false
        }
      })
    },

    getRoleColor (role) {
      const colors = {
        admin: 'red',
        manager: 'orange',
        user: 'blue',
        viewer: 'default'
      }
      return colors[role] || 'default'
    },

    getRoleLabel (role) {
      const labels = {
        admin: this.$t('userManage.roleAdmin') || 'Admin',
        manager: this.$t('userManage.roleManager') || 'Manager',
        user: this.$t('userManage.roleUser') || 'User',
        viewer: this.$t('userManage.roleViewer') || 'Viewer'
      }
      return labels[role] || role
    },

    formatTime (timestamp) {
      if (!timestamp) return ''
      const date = new Date(typeof timestamp === 'number' ? timestamp * 1000 : timestamp)
      return date.toLocaleString()
    },

    formatCredits (credits) {
      if (!credits && credits !== 0) return '0'
      return Number(credits).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
    },

    formatDate (dateStr) {
      if (!dateStr) return ''
      const date = new Date(dateStr)
      return date.toLocaleDateString()
    },

    isVipActive (expiresAt) {
      if (!expiresAt) return false
      return new Date(expiresAt) > new Date()
    },

    // Credits Modal
    showCreditsModal (record) {
      this.creditsEditingUser = record
      this.newCredits = parseFloat(record.credits) || 0
      this.creditsRemark = ''
      this.creditsModalVisible = true
    },

    async handleSetCredits () {
      if (this.newCredits < 0) {
        this.$message.error(this.$t('userManage.creditsNonNegative') || 'Credits cannot be negative')
        return
      }

      this.creditsLoading = true
      try {
        const res = await setUserCredits({
          user_id: this.creditsEditingUser.id,
          credits: this.newCredits,
          remark: this.creditsRemark
        })
        if (res.code === 1) {
          this.$message.success(res.msg || 'Credits updated successfully')
          this.creditsModalVisible = false
          this.loadUsers()
        } else {
          this.$message.error(res.msg || 'Update failed')
        }
      } catch (error) {
        this.$message.error('Update failed')
      } finally {
        this.creditsLoading = false
      }
    },

    // VIP Modal
    showVipModal (record) {
      this.vipEditingUser = record
      this.vipDays = 30
      this.vipCustomDate = null
      this.vipRemark = ''
      this.vipModalVisible = true
    },

    async handleSetVip () {
      const data = {
        user_id: this.vipEditingUser.id,
        remark: this.vipRemark
      }

      if (this.vipDays === -1) {
        if (!this.vipCustomDate) {
          this.$message.error(this.$t('userManage.selectDate') || 'Please select a date')
          return
        }
        data.vip_expires_at = this.vipCustomDate.toISOString()
      } else {
        data.vip_days = this.vipDays
      }

      this.vipLoading = true
      try {
        const res = await setUserVip(data)
        if (res.code === 1) {
          this.$message.success(res.msg || 'VIP status updated successfully')
          this.vipModalVisible = false
          this.loadUsers()
        } else {
          this.$message.error(res.msg || 'Update failed')
        }
      } catch (error) {
        this.$message.error('Update failed')
      } finally {
        this.vipLoading = false
      }
    }
  }
}
</script>

<style lang="less" scoped>
@primary-color: #1890ff;

.user-manage-page {
  padding: 24px;
  min-height: calc(100vh - 120px);
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);

  .page-header {
    margin-bottom: 24px;

    .page-title {
      font-size: 24px;
      font-weight: 700;
      margin: 0 0 8px 0;
      color: #1e3a5f;
      display: flex;
      align-items: center;
      gap: 12px;

      .anticon {
        font-size: 28px;
        color: @primary-color;
      }
    }

    .page-desc {
      color: #64748b;
      font-size: 14px;
      margin: 0;
    }
  }

  .manage-tabs {
    /deep/ .ant-tabs-bar {
      margin-bottom: 20px;
    }
  }

  // Summary Cards
  .summary-cards {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 20px;

    .summary-card {
      background: #fff;
      border-radius: 12px;
      padding: 20px;
      display: flex;
      align-items: center;
      gap: 16px;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
      transition: transform 0.2s, box-shadow 0.2s;

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
      }

      .summary-icon {
        width: 48px;
        height: 48px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;

        .anticon {
          font-size: 22px;
          color: #fff;
        }
      }

      .summary-info {
        flex: 1;
        min-width: 0;

        .summary-value {
          font-size: 22px;
          font-weight: 700;
          color: #1e293b;
          line-height: 1.3;

          .roi-badge {
            font-size: 13px;
            font-weight: 600;
            margin-left: 6px;
            padding: 1px 6px;
            border-radius: 4px;
            background: rgba(0, 0, 0, 0.04);
          }
        }

        .summary-label {
          font-size: 13px;
          color: #94a3b8;
          margin-top: 2px;
        }
      }
    }
  }

  .toolbar {
    margin-bottom: 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;

    .toolbar-left {
      display: flex;
      gap: 12px;
    }

    .toolbar-right {
      display: flex;
      gap: 12px;
    }
  }

  .user-table-card {
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);

    .text-muted {
      color: #94a3b8;
    }
  }

  // PnL colors
  .text-profit {
    color: #52c41a;
    font-weight: 600;
  }

  .text-loss {
    color: #ff4d4f;
    font-weight: 600;
  }

  .pnl-value {
    font-size: 14px;
  }

  .roi-text {
    font-size: 12px;
    margin-left: 4px;
  }

  .pnl-detail {
    font-size: 11px;
    margin-top: 2px;
  }

  .symbol-text {
    font-weight: 500;
  }

  .symbol-count {
    font-size: 11px;
    margin-top: 2px;
  }

  // Status cell
  .status-cell {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;

    .status-dot {
      display: inline-block;
      width: 7px;
      height: 7px;
      border-radius: 50%;
      flex-shrink: 0;

      &.dot-running {
        background: #52c41a;
        box-shadow: 0 0 6px rgba(82, 196, 26, 0.5);
        animation: pulse-green 2s infinite;
      }

      &.dot-stopped {
        background: #d9d9d9;
      }
    }

    .status-running {
      color: #52c41a;
      font-weight: 500;
      font-size: 13px;
    }

    .status-stopped {
      color: #999;
      font-size: 13px;
    }
  }

  @keyframes pulse-green {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  // User cell
  .user-cell {
    display: inline-flex;
    align-items: center;
    max-width: 100%;
    overflow: hidden;
    white-space: nowrap;
    cursor: default;

    .user-name {
      font-size: 13px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 80px;
    }
  }

  .indicator-name {
    color: #722ed1;
    font-size: 12px;
  }

  .exchange-name {
    font-size: 12px;
    text-transform: capitalize;
  }

  // Dark theme
  &.theme-dark {
    background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);

    .page-header {
      .page-title {
        color: #e0e6ed;
      }
      .page-desc {
        color: #8b949e;
      }
    }

    .manage-tabs {
      /deep/ .ant-tabs-bar {
        border-bottom-color: #30363d;
      }
      /deep/ .ant-tabs-tab {
        color: #8b949e;
        &:hover {
          color: #c9d1d9;
        }
      }
      /deep/ .ant-tabs-tab-active {
        color: @primary-color;
      }
    }

    .summary-cards .summary-card {
      background: #1e222d;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);

      .summary-info {
        .summary-value {
          color: #e0e6ed;

          .roi-badge {
            background: rgba(255, 255, 255, 0.08);
          }
        }
        .summary-label {
          color: #6e7681;
        }
      }
    }

    .user-table-card {
      background: #1e222d;
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.25);

      /deep/ .ant-card-body {
        background: #1e222d;
      }

      /deep/ .ant-table {
        background: #1e222d;
        color: #c9d1d9;

        .ant-table-thead > tr > th {
          background: #252a36;
          color: #e0e6ed;
          border-bottom-color: #30363d;
        }

        .ant-table-tbody > tr > td {
          border-bottom-color: #30363d;
        }

        .ant-table-tbody > tr:hover > td {
          background: #252a36;
        }
      }

      .text-muted {
        color: #6e7681;
      }
    }
  }

  // Credits value style
  .credits-value {
    font-weight: 600;
    color: #722ed1;
  }

  // Current info styles
  .current-credits-info,
  .current-vip-info {
    margin-bottom: 16px;
    padding: 12px 16px;
    background: #f5f5f5;
    border-radius: 8px;
    display: flex;
    align-items: center;
    gap: 12px;

    .label {
      color: #666;
    }

    .value {
      font-weight: 600;
      color: #1890ff;
      font-size: 18px;

      &.active {
        color: #52c41a;
      }

      &.expired {
        color: #999;
      }
    }
  }
}

// Responsive
@media (max-width: 1200px) {
  .summary-cards {
    grid-template-columns: repeat(2, 1fr) !important;
  }
}

@media (max-width: 768px) {
  .summary-cards {
    grid-template-columns: 1fr !important;
  }
}
</style>

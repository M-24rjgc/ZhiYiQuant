import { asyncRouterMap } from '@/config/router.config'
import storage from 'store'
import { USER_INFO, USER_ROLES } from '@/store/mutation-types'

/**
 * Filter routes based on user permissions.
 * Routes with meta.permission containing 'admin' are only visible to admin users.
 *
 * @param {Array} routes - Route configuration array
 * @param {boolean} isAdmin - Whether current user is admin
 * @returns {Array} Filtered routes
 */
function filterRoutesByPermission (routes, isAdmin) {
  const filtered = []

  for (const route of routes) {
    // Clone route to avoid mutating original
    const clonedRoute = { ...route }

    // Check if route requires admin permission
    const permissions = clonedRoute.meta?.permission || []
    const requiresAdmin = permissions.includes('admin')

    // If requires admin but user is not admin, skip this route
    if (requiresAdmin && !isAdmin) {
      continue
    }

    // Recursively filter children
    if (clonedRoute.children && clonedRoute.children.length > 0) {
      clonedRoute.children = filterRoutesByPermission(clonedRoute.children, isAdmin)
    }

    filtered.push(clonedRoute)
  }

  return filtered
}

/**
 * Check if current user is admin.
 * Checks both userInfo.role and stored roles array.
 *
 * @returns {boolean} True if user is admin
 */
function checkIsAdmin () {
  // Check userInfo.role first
  const userInfo = storage.get(USER_INFO) || {}
  if (userInfo.role) {
    const roleId = typeof userInfo.role === 'string' ? userInfo.role : userInfo.role.id
    if (roleId === 'admin') {
      return true
    }
  }

  // Check stored roles array
  const roles = storage.get(USER_ROLES) || []
  if (Array.isArray(roles)) {
    for (const role of roles) {
      if (role && (role.id === 'admin' || role === 'admin')) {
        return true
      }
    }
  }

  return false
}

/**
 * Generate dynamic routes based on user permissions.
 * Filters admin-only routes for non-admin users.
 *
 * @param {string} token - User token (unused, kept for compatibility)
 * @returns {Promise<Array>} Promise resolving to filtered routes
 */
export const generatorDynamicRouter = token => {
  return new Promise((resolve) => {
    const isAdmin = checkIsAdmin()

    // Filter routes based on permissions
    const filteredRoutes = filterRoutesByPermission(asyncRouterMap, isAdmin)

    resolve(filteredRoutes)
  })
}

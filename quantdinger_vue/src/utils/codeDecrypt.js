/**
 * 指标代码解密工具
 * 用于解密用户购买的加密指标代码
 */

import CryptoJS from 'crypto-js'
import request from '@/utils/request'

/**
 * 解密指标代码
 *
 * @param {string} encryptedCode - base64编码的加密代码
 * @param {number} userId - 用户ID
 * @param {number} indicatorId - 指标ID
 * @param {string} serverSecret - 服务器密钥（需要从后端获取或配置）
 * @returns {string} - 解密后的代码
 */
export function decryptCode (encryptedCode, userId, indicatorId, encryptedKey) {
  if (!encryptedCode || !userId || !indicatorId || !encryptedKey) {
    return encryptedCode
  }

  try {
    // 解码base64加密代码
    const combined = CryptoJS.enc.Base64.parse(encryptedCode)

    // 提取IV（前16字节）和加密数据
    const ivWords = CryptoJS.lib.WordArray.create(combined.words.slice(0, 4)) // 前16字节（4个word）
    const encryptedWords = CryptoJS.lib.WordArray.create(combined.words.slice(4)) // 剩余部分

    // 解密密钥（从后端获取的base64编码密钥）
    // encryptedKey 是从后端获取的 base64 编码的密钥，直接解码使用
    const key = CryptoJS.enc.Base64.parse(encryptedKey)

    // 解密
    const decrypted = CryptoJS.AES.decrypt(
      { ciphertext: encryptedWords },
      key,
      {
        iv: ivWords,
        mode: CryptoJS.mode.CBC,
        padding: CryptoJS.pad.Pkcs7
      }
    )

    // 转换为字符串
    const decryptedText = decrypted.toString(CryptoJS.enc.Utf8)

    if (!decryptedText) {
      return encryptedCode
    }

    return decryptedText
  } catch (error) {
    // 解密失败，返回原代码（向后兼容）
    return encryptedCode
  }
}

/**
 * 从后端获取解密密钥（动态密钥）
 *
 * @param {number} userId - 用户ID
 * @param {number} indicatorId - 指标ID
 * @returns {Promise<string>} - 解密密钥（base64编码）
 */
export async function getDecryptKey (userId, indicatorId) {
  if (!userId || !indicatorId) {
    throw new Error('用户ID和指标ID不能为空')
  }

  try {
    // 动态请求方式：从后端API获取
    const response = await request({
      url: '/api/indicator/getDecryptKey',
      method: 'post',
      data: {
        userid: userId,
        indicatorId: indicatorId
      }
    })

    if (response.code === 1 && response.data && response.data.key) {
      // 返回base64编码的密钥
      return response.data.key
    } else {
      throw new Error(response.msg || '获取解密密钥失败')
    }
  } catch (error) {
    // 如果后端接口失败，抛出错误，不使用备用密钥（更安全）
    throw new Error('无法获取解密密钥，请检查网络连接或联系管理员: ' + (error.message || '未知错误'))
  }
}

/**
 * 智能解密代码（自动获取密钥）
 *
 * @param {string} encryptedCode - 加密的代码
 * @param {number} userId - 用户ID
 * @param {number} indicatorId - 指标ID
 * @returns {Promise<string>} - 解密后的代码
 */
export async function decryptCodeAuto (encryptedCode, userId, indicatorId) {
  // 从后端动态获取解密密钥（base64编码）
  const encryptedKey = await getDecryptKey(userId, indicatorId)
  // 使用获取的密钥解密
  return decryptCode(encryptedCode, userId, indicatorId, encryptedKey)
}

/**
 * 检查代码是否需要解密
 *
 * @param {string} code - 代码
 * @param {number} isEncrypted - 是否加密标记
 * @returns {boolean}
 */
export function needsDecrypt (code, isEncrypted) {
  // 如果明确标记为加密，或者代码长度很长且符合base64格式，可能需要解密
  if (isEncrypted === 1 || isEncrypted === true) {
    return true
  }

  // 简单检查：加密代码通常较长（base64编码会增大约33%）
  if (code && code.length > 100) {
    // 尝试base64解码检查
    try {
      const decoded = atob(code)
      // 如果解码后的长度合理，可能是加密的
      if (decoded.length > 50) {
        return true
      }
    } catch (e) {
      // 不是base64，不需要解密
    }
  }

  return false
}

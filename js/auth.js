/**
 * 认证与AES解密模块
 * 使用 Web Crypto API + scrypt 兼容后端加密
 * 由于 Web Crypto 不原生支持 scrypt，改用前端 JS 实现
 */

const Auth = (() => {
  const STORAGE_KEY = 'lab_dashboard_pwd';

  // scrypt 参数（与 Python 端一致）
  const SCRYPT_N = 16384; // 2^14
  const SCRYPT_R = 8;
  const SCRYPT_P = 1;
  const KEY_LEN = 32;

  /**
   * 简化版 scrypt（基于 PBKDF2-SHA256 替代，满足实验室安全需求）
   * 为避免引入大型库，使用 PBKDF2 替代 scrypt
   * 注意：加密端也需要对应调整
   */

  function getPassword() {
    return sessionStorage.getItem(STORAGE_KEY);
  }

  function setPassword(pwd) {
    sessionStorage.setItem(STORAGE_KEY, pwd);
  }

  function clearPassword() {
    sessionStorage.removeItem(STORAGE_KEY);
  }

  function isLoggedIn() {
    return !!getPassword();
  }

  /**
   * 从 base64 payload 解密数据
   * 格式: base64(salt[16] + nonce[16] + tag[16] + ciphertext)
   */
  async function decryptData(encBase64, password) {
    const raw = Uint8Array.from(atob(encBase64), c => c.charCodeAt(0));

    const salt = raw.slice(0, 16);
    const nonce = raw.slice(16, 32);
    const tag = raw.slice(32, 48);
    const ciphertext = raw.slice(48);

    // 派生 AES key（使用 PBKDF2 替代 scrypt）
    const keyMaterial = await crypto.subtle.importKey(
      'raw',
      new TextEncoder().encode(password),
      'PBKDF2',
      false,
      ['deriveBits']
    );

    const keyBits = await crypto.subtle.deriveBits(
      { name: 'PBKDF2', hash: 'SHA-256', salt: salt, iterations: 10000 },
      keyMaterial,
      256
    );

    const key = await crypto.subtle.importKey(
      'raw', keyBits, { name: 'AES-GCM' }, false, ['decrypt']
    );

    // AES-GCM 解密（tag 附在 ciphertext 后面）
    const combined = new Uint8Array(ciphertext.length + tag.length);
    combined.set(ciphertext);
    combined.set(tag, ciphertext.length);

    try {
      const decrypted = await crypto.subtle.decrypt(
        { name: 'AES-GCM', iv: nonce },
        key,
        combined
      );
      return new TextDecoder().decode(decrypted);
    } catch (e) {
      return null; // 密码错误
    }
  }

  /**
   * 验证密码（尝试解密 timeline.enc，最小的文件）
   */
  async function verifyPassword(password) {
    try {
      const resp = await fetch('data/timeline.enc');
      if (!resp.ok) return false;
      const encData = await resp.text();
      const result = await decryptData(encData, password);
      return result !== null;
    } catch (e) {
      return false;
    }
  }

  /**
   * 登录
   */
  async function login(password) {
    const valid = await verifyPassword(password);
    if (valid) {
      setPassword(password);
      return true;
    }
    return false;
  }

  function logout() {
    clearPassword();
    window.location.href = 'index.html';
  }

  /**
   * 页面保护 - 在需要认证的页面调用
   */
  function requireAuth() {
    if (!isLoggedIn()) {
      window.location.href = 'index.html';
      return false;
    }
    return true;
  }

  return {
    getPassword, setPassword, clearPassword,
    isLoggedIn, decryptData, verifyPassword,
    login, logout, requireAuth
  };
})();

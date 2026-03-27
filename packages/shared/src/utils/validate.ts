/** 验证中国大陆手机号 */
export function isValidPhone(phone: string): boolean {
  return /^1[3-9]\d{9}$/.test(phone);
}

/** 验证6位数字验证码 */
export function isValidCode(code: string): boolean {
  return /^\d{6}$/.test(code);
}

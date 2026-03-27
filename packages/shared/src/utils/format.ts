/** 格式化日期 */
export function formatDate(date: string | Date, fmt = 'YYYY-MM-DD HH:mm'): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  const pad = (n: number) => String(n).padStart(2, '0');

  const map: Record<string, string> = {
    YYYY: String(d.getFullYear()),
    MM: pad(d.getMonth() + 1),
    DD: pad(d.getDate()),
    HH: pad(d.getHours()),
    mm: pad(d.getMinutes()),
    ss: pad(d.getSeconds()),
  };

  return fmt.replace(/YYYY|MM|DD|HH|mm|ss/g, (m) => map[m] || m);
}

/** 格式化时长（秒 → 中文） */
export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}秒`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return m > 0 ? `${h}小时${m}分钟` : `${h}小时`;
}

/** 格式化数字（千分位） */
export function formatNumber(n: number): string {
  return n.toLocaleString('zh-CN');
}

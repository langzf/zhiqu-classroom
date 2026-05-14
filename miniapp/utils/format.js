function formatDateTime(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const m = `${date.getMonth() + 1}`.padStart(2, '0');
  const d = `${date.getDate()}`.padStart(2, '0');
  const h = `${date.getHours()}`.padStart(2, '0');
  const min = `${date.getMinutes()}`.padStart(2, '0');
  return `${m}-${d} ${h}:${min}`;
}

function sceneLabel(scene) {
  const labels = {
    free_chat: '自由对话',
    homework_help: '答疑解惑',
    review: '复习巩固',
    quiz: '测验练习',
    exploration: '知识探索',
    concept_explain: '概念讲解',
    review_guide: '复习引导',
    error_analysis: '错题分析'
  };
  return labels[scene] || scene || '对话';
}

module.exports = {
  formatDateTime,
  sceneLabel
};

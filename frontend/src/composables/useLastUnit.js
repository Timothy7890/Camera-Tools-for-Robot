import { ref } from 'vue'

// 记住用户最近一次选择的机器人编号，切换页签后再回来时恢复到该机器人的页面。
// 存入 localStorage，刷新后仍然保留。
const STORAGE_KEY = 'calib:lastUnit'

const lastUnit = ref(localStorage.getItem(STORAGE_KEY) || '')

export function useLastUnit() {
  function setLastUnit(unitCode) {
    lastUnit.value = unitCode || ''
    if (lastUnit.value) localStorage.setItem(STORAGE_KEY, lastUnit.value)
    else localStorage.removeItem(STORAGE_KEY)
  }

  return { lastUnit, setLastUnit }
}

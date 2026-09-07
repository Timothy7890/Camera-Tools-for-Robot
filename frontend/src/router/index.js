import { createRouter, createWebHistory } from 'vue-router'
import GuideView from '../views/GuideView.vue'
import CameraCalibView from '../views/CameraCalibView.vue'
import ToolCalibView from '../views/ToolCalibView.vue'

const routes = [
  { path: '/', redirect: '/camera-calibration' },
  { path: '/guide', name: 'guide', component: GuideView, meta: { title: '使用说明' } },
  {
    path: '/camera-calibration',
    name: 'camera-calibration',
    component: CameraCalibView,
    meta: { title: '相机标定文件' },
  },
  {
    path: '/tool-calibration',
    name: 'tool-calibration',
    component: ToolCalibView,
    meta: { title: '工具标定文件' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router

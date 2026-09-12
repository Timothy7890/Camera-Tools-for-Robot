import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import GuideView from '../views/GuideView.vue'
import RobotDetailView from '../views/RobotDetailView.vue'

const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/guide', name: 'guide', component: GuideView, meta: { title: '使用说明' } },
  {
    // 选中某台机器人编号后的详情页，如 /robots/H2-1336/extrinsic
    // section 可选：extrinsic | intrinsic | camera-transform | hand-mount | tcp-profile
    path: '/robots/:unitCode/:section?',
    name: 'robot-detail',
    component: RobotDetailView,
    meta: { title: '标定文件' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router

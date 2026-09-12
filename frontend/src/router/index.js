import { createRouter, createWebHistory } from 'vue-router'

const HomeView = () => import('../views/HomeView.vue')
const GuideView = () => import('../views/GuideView.vue')
const RobotDetailView = () => import('../views/RobotDetailView.vue')

const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/guide', name: 'guide', component: GuideView, meta: { title: '使用说明' } },
  {
    // 选中某台机器人编号后的详情页，如 /robots/H2-1336/camera
    // section 可选：camera | camera-transform | hand-mount | tcp-profile
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

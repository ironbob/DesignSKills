import { defineStore } from 'pinia'

// 全局 UI 态：当前视图 + 打开的工作台项目
export const useUiStore = defineStore('ui', {
  state: () => ({
    view: 'products' as 'products' | 'workbench',
    workbenchProjectId: null as number | null,
    wizardOpen: false, // S2 新建向导浮层
  }),
  actions: {
    openWorkbench(projectId: number) {
      this.workbenchProjectId = projectId
      this.view = 'workbench'
    },
    backToProducts() {
      this.view = 'products'
      this.workbenchProjectId = null
    },
  },
})

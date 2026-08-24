import { defineStore } from 'pinia'

// 全局 UI 态：当前视图 + 打开的工作台项目 / revision 修订视图
export const useUiStore = defineStore('ui', {
  state: () => ({
    view: 'products' as 'products' | 'workbench' | 'revision',
    workbenchProjectId: null as number | null,
    revisionProjectId: null as number | null,
    revisionId: null as number | null,
    wizardOpen: false, // S2 新建向导浮层
    revisionWizard: null as { projectId: number; projectName: string } | null, // 增量需求创建浮层
  }),
  actions: {
    openWorkbench(projectId: number) {
      this.workbenchProjectId = projectId
      this.view = 'workbench'
    },
    openRevision(projectId: number, revisionId: number) {
      this.revisionProjectId = projectId
      this.revisionId = revisionId
      this.view = 'revision'
    },
    backToProducts() {
      this.view = 'products'
      this.workbenchProjectId = null
      this.revisionProjectId = null
      this.revisionId = null
    },
  },
})

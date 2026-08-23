import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'

export default withMermaid(
  defineConfig({
    lang: 'zh-CN',
    title: '运营文档',
    description: 'expert-doc-writer 渲染底座 · 述职/技术方案',
    srcDir: 'docs',
    srcExclude: ['**/sections/**'],
    cleanUrls: true,
    // dev 模式允许 import 仓库根的共享数据层（docs/<日期>-<slug>/data/*.facts.json）；
    // build（rollup）本就不受 root 限制。这是 web 端接共享数字源的接线，不含 PPT 逻辑。
    server: { fs: { allow: ['../..'] } },
    themeConfig: {
      outline: { level: [2, 3], label: '本页导航' },
      search: { provider: 'local' },
      nav: [],
      externalLinkIcon: false,
    },
    mermaid: {
      theme: 'base',
      themeVariables: {
        primaryColor: '#DBEAFE',
        primaryBorderColor: '#2563EB',
        lineColor: '#64748B',
        fontSize: '14px',
      },
    },
  }),
)

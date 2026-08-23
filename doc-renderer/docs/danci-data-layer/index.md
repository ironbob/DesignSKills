---
title: Danci 背单词 App 本地数据层重构方案
---

<script setup>
import { onUnmounted } from 'vue'
import { perfImprovement } from '../../.vitepress/data/danci.charts'

if (typeof document !== 'undefined') document.body.dataset.docPreset = 'brief'

onUnmounted(() => {
  if (typeof document !== 'undefined') delete document.body.dataset.docPreset
})
</script>

<div class="doc-head">
<h1 style="margin-top:0;border-bottom:none;padding-bottom:0">Danci 背单词 App 本地数据层重构方案</h1>
<div class="doc-sub">客户端团队技术负责人 · 技术评审会讨论稿 · 2026-08　|　Core Data → GRDB.swift 6.x + 自研增量同步</div>
</div>

<!-- @include: ./sections/s1.md -->
<!-- @include: ./sections/s2.md -->
<!-- @include: ./sections/s3.md -->
<!-- @include: ./sections/s4.md -->
<!-- @include: ./sections/s5.md -->
<!-- @include: ./sections/s6.md -->
<!-- @include: ./sections/s7.md -->

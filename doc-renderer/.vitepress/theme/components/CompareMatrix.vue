<script setup lang="ts">
export interface MatrixRow {
  cells: string[]
  pick?: boolean
}
defineProps<{ columns: string[]; rows: MatrixRow[] }>()
</script>

<template>
  <div class="matrix-wrap">
    <table class="matrix">
      <thead>
        <tr>
          <th v-for="(c, i) in columns" :key="i">{{ c }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(r, i) in rows" :key="i" :class="{ pick: r.pick }">
          <td v-for="(c, j) in r.cells" :key="j">{{ c }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.matrix-wrap { overflow-x: auto; margin: 1rem 0; }
.matrix {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  background: var(--doc-card);
  border: 1px solid var(--doc-line);
  border-radius: 14px;
  overflow: hidden;
  font-size: 14.5px;
}
.matrix th {
  background: #f1f5f9;
  color: var(--doc-muted);
  text-align: left;
  padding: 11px 14px;
  font-size: 13.5px;
  white-space: nowrap;
}
.matrix td {
  padding: 11px 14px;
  border-top: 1px solid var(--doc-line);
  vertical-align: top;
}
.matrix tr.pick td {
  background: var(--doc-accent-weak);
  font-weight: 600;
}
</style>

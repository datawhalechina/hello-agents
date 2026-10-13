<template>
  <div class="graph-canvas">
    <svg :viewBox="`0 0 ${W} ${H}`" class="g-svg" @pointerdown.self="drag = null">
      <g v-for="l in links" :key="`${l.source}-${l.target}-${l.type}`">
        <line
          :x1="pos(l.source).x"
          :y1="pos(l.source).y"
          :x2="pos(l.target).x"
          :y2="pos(l.target).y"
          :class="edgeClass(l.type)"
        />
      </g>
      <g
        v-for="n in nodes"
        :key="n.id"
        :transform="`translate(${pos(n.id).x},${pos(n.id).y})`"
        class="g-node"
        role="button"
        tabindex="0"
        @pointerdown.stop="startDrag(n, $event)"
        @click.stop="onClick(n)"
        @keydown.enter.prevent="selectNode(n)"
        @keydown.space.prevent="selectNode(n)"
      >
        <title>{{ nodeTooltip(n) }}</title>
        <circle
          :r="nodeRadius(n)"
          :class="[
            'node-shape',
            `node-${n.type}`,
            { 'is-center': n.id === centerId, 'is-selected': n.id === selectedId }
          ]"
        />
        <text :y="nodeRadius(n) + 13" class="node-label">{{ shortLabel(n) }}</text>
      </g>
    </svg>
    <div class="legend">
      <span class="legend-item"><i class="dot dot-paper" />文献</span>
      <span class="legend-item"><i class="dot dot-author" />作者</span>
      <span class="legend-item"><i class="dot dot-journal" />期刊</span>
      <span class="legend-item"><i class="line-dot edge-related" />关联</span>
      <span class="tip">拖拽移动节点 · 单击文献节点继续探索</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import type { GraphLink, GraphNode } from '@/types'

const props = defineProps<{
  nodes: GraphNode[]
  links: GraphLink[]
  centerId?: string
  selectedId?: string
}>()

const emit = defineEmits<{ (e: 'select', node: GraphNode): void }>()

const W = 760
const H = 520

interface P {
  x: number
  y: number
}

const positions = reactive<Record<string, P>>({})
const drag = ref<string | null>(null)

function pos(id: string): P {
  return positions[id] ?? { x: W / 2, y: H / 2 }
}

function shortLabel(n: GraphNode): string {
  const label = n.label || n.id
  return label.length > 16 ? label.slice(0, 15) + '…' : label
}

function nodeRadius(n: GraphNode): number {
  if (n.type === 'paper') return n.id === props.centerId ? 26 : 20
  if (n.type === 'author') return 12
  return 14
}

function edgeClass(type: string): string {
  return `g-edge edge-${(type || '').toLowerCase()}`
}

function layout(): void {
  const list = props.nodes
  if (!list.length) return

  const cx = W / 2
  const cy = H / 2
  for (const n of list) {
    positions[n.id] = { x: cx, y: cy }
  }
  const others = list.filter((n) => n.id !== props.centerId)
  const radius = Math.min(200, 70 + others.length * 14)
  others.forEach((n, i) => {
    const angle = (i / Math.max(1, others.length)) * Math.PI * 2
    positions[n.id] = { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) }
  })

  const rep = 26000
  const spring = 0.02
  const rest = 115
  const gravity = 0.02
  const damping = 0.55
  const maxStep = 10

  for (let iter = 0; iter < 260; iter++) {
    const fx: Record<string, number> = {}
    const fy: Record<string, number> = {}
    for (const n of list) {
      fx[n.id] = 0
      fy[n.id] = 0
    }
    for (let i = 0; i < list.length; i++) {
      for (let j = i + 1; j < list.length; j++) {
        const a = list[i]
        const b = list[j]
        const pa = positions[a.id]
        const pb = positions[b.id]
        let dx = pa.x - pb.x
        let dy = pa.y - pb.y
        const d2 = Math.max(dx * dx + dy * dy, 1)
        const d = Math.sqrt(d2)
        const f = rep / d2
        dx /= d
        dy /= d
        fx[a.id] += dx * f
        fy[a.id] += dy * f
        fx[b.id] -= dx * f
        fy[b.id] -= dy * f
      }
    }
    for (const l of props.links) {
      const pa = positions[l.source]
      const pb = positions[l.target]
      if (!pa || !pb) continue
      let dx = pb.x - pa.x
      let dy = pb.y - pa.y
      const d = Math.max(Math.sqrt(dx * dx + dy * dy), 0.001)
      const f = spring * (d - rest)
      dx /= d
      dy /= d
      fx[l.source] += dx * f
      fy[l.source] += dy * f
      fx[l.target] -= dx * f
      fy[l.target] -= dy * f
    }
    for (const n of list) {
      const p = positions[n.id]
      fx[n.id] += (cx - p.x) * gravity
      fy[n.id] += (cy - p.y) * gravity
      p.x += Math.max(-maxStep, Math.min(maxStep, fx[n.id] * damping))
      p.y += Math.max(-maxStep, Math.min(maxStep, fy[n.id] * damping))
      p.x = Math.max(30, Math.min(W - 30, p.x))
      p.y = Math.max(30, Math.min(H - 30, p.y))
    }
  }
}

let dragStart = { x: 0, y: 0, nx: 0, ny: 0 }
let dragMoved = false

function startDrag(n: GraphNode, ev: PointerEvent): void {
  drag.value = n.id
  dragMoved = false
  const p = positions[n.id]
  dragStart = { x: ev.clientX, y: ev.clientY, nx: p.x, ny: p.y }
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUp)
}

function onMove(ev: PointerEvent): void {
  if (!drag.value) return
  const p = positions[drag.value]
  if (!p) return
  if (Math.abs(ev.clientX - dragStart.x) > 4 || Math.abs(ev.clientY - dragStart.y) > 4) {
    dragMoved = true
  }
  p.x = Math.max(30, Math.min(W - 30, dragStart.nx + (ev.clientX - dragStart.x)))
  p.y = Math.max(30, Math.min(H - 30, dragStart.ny + (ev.clientY - dragStart.y)))
}

function onUp(): void {
  drag.value = null
  window.removeEventListener('pointermove', onMove)
  window.removeEventListener('pointerup', onUp)
}

function onClick(n: GraphNode): void {
  if (dragMoved) {
    dragMoved = false
    return
  }
  selectNode(n)
}

function selectNode(n: GraphNode): void {
  emit('select', n)
}

function nodeTooltip(n: GraphNode): string {
  const action = n.type === 'paper' ? '单击设为中心并加载详情' : '单击查看关系'
  return `${n.label || n.id}（${action}）`
}

watch(() => [props.nodes, props.links], () => layout(), { deep: true })
layout()
</script>

<style scoped>
.graph-canvas {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.g-svg {
  width: 100%;
  min-height: 480px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
  touch-action: none;
}
.g-edge {
  stroke: #94a3b8;
  stroke-width: 1.4;
}
.edge-authored {
  stroke: #93c5fd;
}
.edge-published_in {
  stroke: #86efac;
}
.edge-related {
  stroke: #cbd5e1;
  stroke-dasharray: 5 4;
}
.g-node {
  cursor: grab;
}
.node-shape {
  stroke: #fff;
  stroke-width: 1.5;
}
.node-paper {
  fill: #409eff;
}
.node-author {
  fill: #f59e0b;
}
.node-journal {
  fill: #34d399;
}
.is-center {
  stroke: #f59e0b;
  stroke-width: 3.5;
}
.is-selected {
  filter: drop-shadow(0 0 6px rgb(64 158 255 / 70%));
  stroke: #1d4ed8;
  stroke-width: 3.5;
}
.g-node:focus {
  outline: none;
}
.g-node:focus .node-shape {
  stroke: #1d4ed8;
  stroke-width: 3.5;
}
.node-label {
  font-size: 11px;
  fill: #475569;
  text-anchor: middle;
  pointer-events: none;
  user-select: none;
}
.legend {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
.dot-paper {
  background: #409eff;
}
.dot-author {
  background: #f59e0b;
}
.dot-journal {
  background: #34d399;
}
.line-dot {
  width: 18px;
  height: 0;
  border-top: 2px dashed #cbd5e1;
  display: inline-block;
}
.tip {
  margin-left: auto;
  color: var(--el-text-color-placeholder);
}
</style>

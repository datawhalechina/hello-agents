# 贴图来源与制作记录

待机直接复用用户提供的 3D 菲比啾比 PNG，源文件保存为 [phoebe-source.png](phoebe-source.png)，对应的 [phoebe-idle.png](phoebe-idle.png) 保持不变。

用户确认了三态预览：待机沿用原图，悬停双手背后、前倾探头，点击闭眼开心小跳。动作使用内置 `image_gen.imagegen` 透明背景模式生成，以原图作为人物身份参考、确认的预览作为姿态参考。完整最终提示词见 [ACTIONS-PROMPT.md](ACTIONS-PROMPT.md)。生成结果保存为 [phoebe-actions-sheet.png](phoebe-actions-sheet.png)，1536×1024 RGBA，三列两行，每格 512×512；原始生成文件同时保留在本机 Codex 的 `generated_images` 目录。

## 机械编码

- 工具：Node.js 脚本 `desktop/scripts/build-mascot-assets.mjs`。
- 输入：`desktop/electron/assets/phoebe-actions-sheet.png`。
- 输出：256×256 的悬停和点击静态 PNG、透明 GIF 及动画参数 JSON；不覆盖待机原图。
- 悬停：源帧顺序 `0,1,2,1,0`，时长 `180,220,260,220,220` 毫秒，共 1100ms，无限循环。
- 点击：源帧顺序 `3,4,4,5`，时长 `100,180,220,300` 毫秒，共 800ms，单次播放。
- 对六格使用相同的裁切和缩放参数，保留跳跃位置变化，防止逐格归一化造成尺寸闪变。
- 生成图先经过内置 imagegen 透明边缘修订；机械编码时保留人物主连通区域及相邻柔边，丢弃分离的背景碎屑，原始动作图不覆盖。
- 透明度：PNG 保留完整 alpha；GIF 采用共享色板和二值透明，并逐帧清除画布。

## 连续播放与姿态衔接

平滑修复沿用上述人物美术，没有重新设计或生成角色。编码器增加 7 格 PNG 图集和对应关键点数据，保留待机原图像素，将动作帧的靴子落脚位置注册到待机基线。每格包含 25 个对应点，眼睛、闭眼眼线、嘴、帽檐、蝴蝶和靴子坐标结合像素区域测量与人工目检核准；固定的 44 个三角形在全部姿态与中间插值中保持正向。客户端使用 Canvas 和 `requestAnimationFrame`，将相邻姿态的网格对齐后连续插值；跳跃高度由程序的连续轨迹控制，事件和绘制共用单调时钟。GIF 仅作为关键姿态示意保留。

在 `desktop` 目录执行：

```powershell
node scripts/build-mascot-assets.mjs electron/assets/phoebe-actions-sheet.png
```

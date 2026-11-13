# 菲比啾比桌面贴图

待机使用用户选定的 3D 菲比啾比 PNG 原图。悬停和点击动作根据用户确认的预览，使用内置 **imagegen** 生成透明动作帧，再由 Node.js 裁切、清理透明边缘和注册落脚位置。运行时使用 Canvas 连续播放器。

| 文件 | 用途 |
| --- | --- |
| [phoebe-source.png](phoebe-source.png) | 用户选定的原始 3D 透明图，保留原文件 |
| [phoebe-idle.png](phoebe-idle.png) | 256×256 待机图，保留透明 alpha |
| [phoebe-actions-sheet.png](phoebe-actions-sheet.png) | 3 列 × 2 行透明动作图，上排探头，下排小跳 |
| [phoebe-hover.gif](phoebe-hover.gif) | 256×256 透明悬停动画：5 帧、无限循环，每轮 1100ms |
| [phoebe-hover-still.png](phoebe-hover-still.png) | 连续播放器不可用时的 256×256 悬停回退图 |
| [phoebe-click.gif](phoebe-click.gif) | 256×256 透明点击动画：4 帧、单次播放，800ms |
| [phoebe-click-still.png](phoebe-click-still.png) | 连续播放器不可用时的点击静态回退图 |
| [phoebe-animation.json](phoebe-animation.json) | 动画帧顺序、时长、循环方式和统一缩放参数 |
| [phoebe-poses.png](phoebe-poses.png) | 连续播放器使用的 7 格姿态图集，含原始待机和注册后的动作姿态 |
| [phoebe-poses.js](phoebe-poses.js) | 图集坐标、共同落脚位置及每个姿态的 25 个对应关键点 |

[悬停关键帧示意](phoebe-hover.gif) · [点击关键帧示意](phoebe-click.gif)。这些 GIF 保留为素材示意，客户端使用连续播放器。

悬停时双手背到身后、身体前倾、歪头探看；点击时闭眼笑、蓄力、抬手小跳并落地。待机 PNG 与原图文件保持不变。编码器保留每格人物主体及相邻柔边，剔除透明区域里分离的生成碎屑；随后对六格使用同一裁切区域和缩放参数，保留动作位置变化。GIF 使用共享色板、透明索引和逐帧清除；PNG 保留人物柔边透明度，GIF 使用二值透明。

播放器使用 25 个对应关键点和 44 个三角形，对齐头脸、帽檐、蝴蝶、发缘、嘴部、躯干和靴子后，按屏幕刷新节奏插值。小跳采用连续升降轨迹和落地回弹，替代腾空关键帧长时间停留。按压保留当前画面，手势确认后衔接点击；移入、移出和连点都从当前可见姿态及运动速度接续。

事件与绘制使用同一单调动画时钟。原生窗口打开造成短暂阻塞时，后续帧继续播放动作中间过程，避免跳过蓄力或落地；待机和减少动态效果模式停止连续绘制。

点击动作与客户端展开同时开始，失焦不会打断已接受的反馈。拖动和取消手势不会触发点击动作；减少动态效果模式立即使用静态姿态并停止运动。

在 `desktop` 目录重新编码：

```powershell
node scripts/build-mascot-assets.mjs electron/assets/phoebe-actions-sheet.png
```

来源与制作记录见 [GENERATION.md](GENERATION.md)。

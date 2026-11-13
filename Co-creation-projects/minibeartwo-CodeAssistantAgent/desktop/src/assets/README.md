# 客户端首页背景

`client-wallpaper.png` 是首页使用的独立 4:3 插画背景，基于用户确认的界面预览，通过内置 `image_gen` 工具制作。标题、图标、按钮、拖入区域和窗口控制均在 React/CSS 中实现，没有烘焙在背景图片中。

参考：用户提供的 `codex-clipboard-fa6492d6-7578-4301-b14e-119aca99b662.png`。

生成提示词：

> Use case: precise-object-edit. Asset type: clean 4:3 desktop application wallpaper. Edit the supplied screenshot by removing ALL UI overlays: remove the entire top navy title bar, its butterfly logo, ALL text, all window controls; remove the large bottom left panel including dashed border, folder icon, text; remove BOTH bottom right action cards including borders, icons, text, graphic decorations. Inpaint the underlying anime illustration naturally in the vacated areas. Preserve the visible original illustration as exactly as possible: golden-haired purple-eyed smiling Phoebe in white wide-brim witch hat with blue accents, large face at x~64%, y~26%, reaching gloved hand to left; brilliant royal blue magical castle, luminous blue butterflies, gold sparkles and ribbons, same composition, colors and high-detail anime rendering. Full-bleed illustration occupying entire 4:3 canvas, no inset borders. The lower half should continue her flowing blue/white clothes and magical castle naturally. No interface, no cards, no text, no lettering, no logos, no frames, no controls, no panels whatsoever. This asset will sit BEHIND separately implemented live HTML controls.

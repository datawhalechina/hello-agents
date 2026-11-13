# 动作贴图生成提示词

## 透明边缘与帧位置修订提示词

```text
Use case: background-extraction / identity-preserve.
EDIT the attached SIX-POSE 3x2 sprite sheet. Preserve all six character faces, costume, arm poses, eye expressions and 3D style exactly. Do not create new action designs.

This is a production alpha cleanup and sprite registration pass:
1. Remove ALL background pixels and loose disconnected debris around the six characters. Retain only each complete character silhouette. Background must be true transparent alpha with RGB zero outside silhouettes. No grey/beige fragments, stray flecks, floating patches, ground shadows, backdrop, halo or contact shadows.
2. Maintain EXACTLY THREE columns by TWO rows of equal SQUARE cells. Every character including ribbons, hat, curls and boots must sit COMPLETELY inside its own cell with at least 12 percent clear padding on ALL FOUR edges. There must be clear empty transparent channels at the exact column and row boundaries. Current blue ribbons occasionally touch neighboring cells; reduce ALL SIX characters uniformly if needed so that does not happen. No clipping.
3. Uniform scale/camera/head size across all six characters. Standing foot baseline identical across top0, top1, top2, bottom0 and bottom2, approximately 85 percent of cell height. Keep bottom-middle tiny HOP raised above that baseline, same character scale. Do not resize each figure differently.
4. Keep top row ALL hands hidden BEHIND BACK with open violet eyes and curious leaning/tilted head. Bottom row keeps closed-eye smile: hands at chest, hands beside cheeks while hopping, hands near chest on landing.
Keep exact 3D figurine material quality and all details. Do not paint checkerboard, text, frame lines, dividers, arrows, ornaments or motion marks. Output a clean genuinely transparent 3:2 PNG sheet with the six preserved poses, ample spacing, zero visible debris.
```

## 首轮动作生成提示词

模式：内置 `image_gen.imagegen`，透明背景。原图作为人物参考，用户确认的三态预览作为动作参考。

```text
Use case: identity-preserve.
Asset type: production transparent animation sprite sheet for the approved Phoebe desktop mascot.
Input image 1: the EXACT existing original 3D character; definitive identity, materials, costume and proportions.
Input image 2: user-approved action concept board; use ONLY the middle hover poses and right click poses as ACTION REFERENCES. Ignore all text, background, panels and dividers.
Create ONE landscape PNG with a TRUE transparent alpha background. EXACTLY a regular THREE COLUMNS by TWO ROWS grid, SIX equal SQUARE cells. A 3:2 canvas. No labels, no lines, no arrows, no floor shadows, no cursor, no motion marks. Each cell contains only one full-body figure. All cells are mechanically cropped at exact thirds of width and half of height.

Strict identity: same soft high-quality 3D collectible chibi girl as image1, enormous sparkling purple eyes, round face with blush, long pale-blonde curls, white wide-brim hat, blue hatband and blue-white butterfly on viewer right, blue cross hair clip, black gloves, original white/blue/black outfit and white boots. Preserve exact outfit shapes and details, face and head/body ratio. Do NOT change to 2D/anime lineart or redesign. No extra accessories.

Registration is critical: across ALL SIX cells use identical camera, zoom, head size, body size and lighting. The standing figure occupies about 72 percent of cell height, centrally placed; feet baseline around 87 percent of cell height. Keep a minimum 10 percent clear padding from every cell boundary, including the hat brim and hair. Do NOT individually enlarge poses to fill each cell. All silhouettes completely inside their cells. Only the jumping frame has elevated feet, no resizing.

TOP ROW = hover animation, LEFT TO RIGHT three consecutive poses.
0 / top-left: approved curious hover. BOTH arms LOWERED behind her back, gloved hands hidden behind waist, no raised hand at all. Legs together, torso gently leaning forward, head gently tilted toward viewer right about 8 degrees, purple eyes OPEN, tiny curious closed smile. This silhouette must be obviously different from the original raised-hand idle.
1 / top-middle: same arms-behind-back pose and planted boots, head tilts a little farther toward viewer right about 15 degrees, torso leans forward a little more, eyes OPEN looking curiously outward, mouth forms a tiny surprised o. Hair follows slight tilt.
2 / top-right: same planted feet and BOTH hands remaining behind her back, torso starts to rise slightly and head tilt eases toward 10 degrees, purple eyes OPEN, tiny soft smile. No blink, no wink, NO WAVING or hand gesture anywhere in the TOP ROW.

BOTTOM ROW = click feedback, LEFT TO RIGHT three consecutive poses.
3 / bottom-left: happy anticipation, both black-gloved hands together at chest, knees bent a little with boots still on baseline, eyes closed into joyful curved crescents, broad small smile. Same character, no extra fingers.
4 / bottom-middle: tiny joyous HOP, feet visibly lifted around 6 percent of cell height above standing baseline, knees tucked slightly, BOTH gloved hands raised beside cheeks, closed smiling eyes, joyful open little mouth. Hair tips and ribbons lift naturally. Complete hat remains within cell. No scaling or zoom.
5 / bottom-right: gentle LANDING, boots return to standing baseline, knees soften, both hands lower near chest, eyes still happily closed, warm smile, hair settling. Identical camera, scale and costume.

This is artwork only, with genuine transparent background. No painted checkerboard, no solid coloured backdrop, no Chinese text, no captions, no borders, no ground plane or contact shadow. Keep the 3D identity as close to image1 as possible while matching approved middle/right actions in image2.
```

# maps-workflow · 高德地图调研流程与兜底

本文件是所有调研的地图数据来源，先读它再执行具体活动专项。

## 可用工具（高德 MCP，名称以本 Agent 实际环境为准）

- 关键词搜索：`maps_text_search`（keywords + city）
- 周边搜索：`maps_around_search`（location + radius + keywords）
- POI 详情：`maps_search_detail`（id）
- 地址→坐标：`maps_geo`；坐标→地址：`maps_regeocode`
- 距离测量：`maps_distance`（type：1 驾车 / 2 骑行 / 3 步行）
- 驾车路线：`maps_direction_driving_by_address` / `maps_direction_driving_by_coordinates`
- 步行路线：`maps_direction_walking_by_address` / `maps_direction_walking_by_coordinates`
- 骑行路线：`maps_bicycling_by_address` / `maps_bicycling_by_coordinates`
- 公交路线：`maps_direction_transit_integrated_by_address` / `maps_direction_transit_integrated_by_coordinates`
- 天气：`maps_weather`（按城市或 adcode，户外方案必查）
- IP 定位：`maps_ip_location`

若实际环境工具名不同，用能力描述代替，例如“调用高德关键词搜索工具”。

## 调研顺序

1. 定位城市：`maps_geo` 拿城市中心坐标（city 填用户城市）。
2. 找锚点：按活动类型用 `maps_text_search` / `maps_around_search` 搜索真实 POI。
3. 查详情：`maps_search_detail` 拿地址、电话、坐标，以及 biz_ext 中的人均/营业时间/评分（如有）。
4. 算距离：`maps_distance` 或 `maps_direction_*` 计算各候选点间通勤时间。
5. 验证衔接：按锚点时间倒推，确认每段通勤时间是否满足衔接。

## 筛选规则

- 城市内筛选：检查 POI 坐标是否在用户城市范围，排除下辖县/郊区的远距离结果。
- 排除用户明确不喜欢的类型（如“不去人多商场”）。
- 优先顺路、距离近、评分高、信息全的地点。
- 每套方案先找固定活动锚点，再补餐饮、咖啡和续场地点。

## 失败兜底（重要）

- 若当前 Agent 实例的 `maps_*` 工具路由不可用（报“未知工具”），改用 `code_run` 直调高德 REST API：
  - Key：`temp/amap_key.txt`（只引用文件，不读取密钥内容以外的数据）。
  - 端点：`/v3/place/text`（关键词搜索）、`/v3/place/around`（周边）、`/v3/place/detail`（详情）、`/v3/distance`（距离）、`/v3/direction/*`（路线）。
  - 注意：`urllib` 请求高德可能报 `SSL: UNEXPECTED_EOF`，优先用 `curl.exe` 请求并做 2~3 次重试。
- API 未返回价格/营业时间/评分时，一律标“需要确认”，不得编造。
- 网络连续失败 2 次：探测环境状态；3 次：换方案或请求用户干预。

## 动态信息核验

- 高德只有静态 POI 信息（位置、电话、营业时间等）。
- 电影排片、展览场次、演出余票、预约规则等动态信息必须用网页搜索或浏览器（web 工具 / google）核实。
- 信息来源要区分：已确认信息 / 单一来源信息 / 尚未确认信息，输出时如实标注。

# 工程工具箱 — 设计改造实验已回滚

## 现状

本目录曾在 2026-07-14 通过 commit cb95f04、0ae0142、3befdcd 提交过设计改造版本
(三色坐标系、深色主题、点击地图选点、搜索历史等)。

由于改造在跟百度地图 GL v1.0 API 集成时遇到无法可靠复现的级联问题
(地图加载后无法点击、BMapGL 未就绪时调用导致脚本崩溃等),
三次修复尝试均失败,最终服务器端回滚到 1575 行原始版本。

## 当前线上版本

服务器 /root/map-coord-tool/index.html 是 1536-1575 行原始版本,未做设计改造。

## 未来如果再做设计改造

1. 隔离实验:在 design-prototype.html 独立文件中做样式主题试验
2. 保留下拉兼容性:保留原版 position:absolute + overflow-y:auto,不要换 fixed
3. 保留地图事件 inline:click handler 必须在 initMap 函数体内注册
4. 避免 renderOptions:{map:map,panel:null}:让百度 LocalSearch 不要自动绑地图
5. 每次只改一件事,改完用浏览器实际验证有效,再 commit

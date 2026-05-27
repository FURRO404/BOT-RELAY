# AXBot Scoreboard Assets

## English
This directory is the default asset root for `src.scoreboard`.

Expected layout:
- `MAPS/` - map background images, one image per map name
- `ICONS/` - header icons and vehicle icons
- `ICONS/VEHICLES/` - per-vehicle PNG icons, keyed by vehicle internal name
- `FONTS/arial_unicode_ms.otf` - Unicode-safe font used by the renderer

If you already have the SREBOT asset bundle, you can point AXBot at it with:

```bash
export AXBOT_SCOREBOARD_ASSETS_DIR=/path/to/assets
```

The renderer also looks for the sibling SREBOT asset bundle in the workspace when the env var is not set.

## 中文
这个目录是 `src.scoreboard` 的默认资源根目录。

期望的目录结构：
- `MAPS/` - 地图背景图片，每张地图一张图
- `ICONS/` - 标题图标和载具图标
- `ICONS/VEHICLES/` - 按载具 internal name 命名的 PNG 图标
- `FONTS/arial_unicode_ms.otf` - 渲染器使用的 Unicode 安全字体

如果你已经有 SREBOT 的资源包，可以这样指向它：

```bash
export AXBOT_SCOREBOARD_ASSETS_DIR=/path/to/assets
```

如果没有设置该环境变量，渲染器也会尝试使用工作区里旁边的 SREBOT 资源包。

# 文档与图表维护

正文来源为根目录 `电子琴设计_技术文档.md`。`GENERATED_APPENDIX` 标记后的内容由源码索引脚本生成；修改这部分说明时编辑 `build_appendix.py` 中的说明表，然后重新构建。

Python 依赖：Python 3.11+、Markdown、beautifulsoup4；数值图还需要 matplotlib、numpy、Pillow。Mermaid 渲染需要 Node.js、Playwright、Microsoft Edge（或将脚本改为已安装的 Chromium 通道）及 Mermaid 10.9.3 的 `dist/mermaid.min.js`。所有生成物均已提供，阅读文件无需安装依赖。

```powershell
python -m pip install -r tools/requirements.txt
npm install --prefix tools
python tools/build_docs.py
python tools/create_diagrams.py
python tools/draw_plots.py
python tools/create_showcase.py
node tools/render_diagrams.cjs tools/node_modules/mermaid/dist/mermaid.min.js
node tools/render_visuals.cjs
```

`build_docs.py` 同步附录、HTML、项目首页与源码阅读页。源码阅读页采用 UTF-8 编码，支持中文注释和行号跳转。

项目首页在 `home.template.html` 中编辑，样式位于 `assets/styles/showcase.css`。`create_showcase.py` 生成封面、操作图、设计过程图与技术标签，`render_visuals.cjs` 使用 Sharp 导出 PNG；`render_cover.cjs` 是同一渲染入口。代码着色使用 Pygments。

`create_diagrams.py` 是架构图、流程图和六张原生 SVG 的来源。修改流程结构时编辑脚本中的定义；`assets/diagrams` 中的 `.mmd` 是可独立使用的图源；系统总览、模式图与调试流程图采用等价关系的人工排布SVG，由Python脚本统一生成。`draw_plots.py` 保存参数推导图，并在本机安装了 scipilot-figure-skill 时使用其字体样式与布局检查；无该技能时采用内置中文字体配置。

HTML 使用本地 CSS、JS、SVG、照片与视频，可双击打开；源码链接跳转到本地行号页。Markdown 的源码链接指向保留的工程文件，适用于 GitHub 仓库浏览。发布时使用根目录 `index.html` 作为 GitHub Pages 首页，无需在线运行 Python 或 Node。

每次更新后核对：正文和HTML内容一致、目录能跳转、变量解释与源码一致、所有图可显示、手机端表格局部滚动、视频可播放。修改固件后还需重新核对相关参数并在适用工具链与目标板上验证。

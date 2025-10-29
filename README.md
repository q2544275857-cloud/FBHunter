# FB Hunter — 主页采集 · 关键词+地区 · 独立缓存 · 详细异常原因

## 功能
- ✅ **只采集 Facebook 主页/个人主页**（过滤 posts/groups/events/photos/videos/reels 等）
- ✅ **关键词 + 地区** 采集（同地区与不同地区缓存独立）
- ✅ **历史采集缓存**：cache/<关键词_地区>/cache.db，重复运行自动跳过已采 URL
- ✅ **日志详细显示异常原因**（代理错误、网络超时、无结果、频率限制等）
- ✅ **导出到项目根目录 data/**：文件名 `关键词_地区_日期.csv`；多关键词时 `multi_地区_日期.csv`
- ✅ **多线程 + QThread**：日志实时上屏、进度条

## 安装
```bash
pip install -r requirements.txt
python -m playwright install chromium
python main.py
```

## 打包为单 EXE
```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --onefile --name "FBHunter" --add-data "fb_hunter;fb_hunter" main.py
```

> 首次运行会在系统 AppData 下创建 `cookies/` 与 `logs/`；采集/导出目录在**项目根目录**的 `cache/` 与 `data/`。

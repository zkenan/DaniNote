# 张张便签 (Znote) - 打包说明

## 打包方式

提供了三种打包脚本，选择一种即可：

### 1. 使用批处理文件 (推荐)
双击运行 `package.bat`

### 2. 使用 Python 脚本
直接运行 `python package.py`

### 3. 使用 PowerShell 脚本
右键点击 `package.ps1` → 选择"使用 PowerShell 运行"

> **重要更新**：应用已更名为 **"张张便签" (Znote)**，版本 v0.1.0，打包产物命名格式：`Znote_Win64_v0.1.0_{时间戳}.exe`

## 打包前准备

1. **确保已安装 Python 3.8+**
   - 打开命令提示符，输入 `python --version` 确认版本
   - 如果未安装，请从 [python.org](https://www.python.org/) 下载并安装
   - 安装时勾选 "Add Python to PATH"

2. **确保已安装 PyInstaller**
   - 脚本会自动检测并安装，但也可以手动安装：
   ```cmd
   pip install pyinstaller
   ```

## 打包过程

1. 脚本会：
   - 清理旧的构建文件 (`build/`, `dist/`, `*.spec`)
   - 使用 PyInstaller 打包
   - 包含所有必要的依赖和资源文件

2. 打包时间：约 5-15 分钟，取决于电脑性能

3. 输出文件：`dist/Znote_Win64_v0.1.0_{时间戳}.exe` (约 45-50 MB)

## 运行程序

打包完成后：
- 双击 `dist/Znote_Win64_v0.1.0_{时间戳}.exe` 即可运行
- 程序会在后台运行，右下角系统托盘显示图标
- 右键托盘图标可退出程序

## 常见问题

### 1. 打包失败
- 检查 Python 和 PyInstaller 是否正确安装
- 确保有足够的磁盘空间 (至少 2 GB)
- 关闭杀毒软件，可能会误报
- **如果出现 `'d' 不是内部或外部命令` 等错误**：这是批处理文件编码问题，请改用 `python package.py` 或更新后的 `package.bat`

### 2. 运行时报错
- 确保 `dist/` 文件夹包含完整的 `assets/` 和 `src/` 数据
- 如果提示缺少 DLL，可能需要安装 Visual C++ Redistributable
- 如果提示缺少模块，检查 `package.py` 中的 `--hidden-import` 参数

### 3. 文件太大
- 这是正常的，因为 PyInstaller 会打包 Python 解释器和所有依赖
- 使用 `--onefile` 选项生成单个 EXE，方便分发
- 最终 EXE 约 45-50 MB

## 手动打包命令

> 注意：以下命令在 CMD 中可能因中文字符编码问题失败，建议直接使用 `package.bat` 或 `python package.py`。

如果脚本有问题，也可以手动创建 Python 打包调用：

```python
# 在 Python 中执行
import subprocess, sys
subprocess.run([
    sys.executable, "-m", "PyInstaller",
    "--onefile", "--windowed",
    "--name", "Znote_Win64_v0.1.0_202605291500",
    "--icon", "assets/app.ico",
    "--add-data", "src;src",
    "--add-data", "assets;assets",
    "--add-data", "version.py;.",
    "--hidden-import", "PySide6.QtCore",
    "--hidden-import", "PySide6.QtGui",
    "--hidden-import", "PySide6.QtWidgets",
    "--hidden-import", "PySide6.QtPrintSupport",
    "--hidden-import", "sqlite3",
    "--hidden-import", "ctypes",
    "--hidden-import", "ctypes.wintypes",
    "--hidden-import", "json",
    "--hidden-import", "datetime",
    "--hidden-import", "version",
    "--hidden-import", "src",
    "--hidden-import", "src.utils",
    "--hidden-import", "src.utils.notifier",
    "--hidden-import", "src.models",
    "--hidden-import", "src.views",
    "--hidden-import", "src.views.main_window",
    "--hidden-import", "src.views.note_editor",
    "--hidden-import", "src.views.settings_panel",
    "--hidden-import", "src.image_manager",
    "--collect-submodules", "src.utils",
    "--collect-submodules", "src.views",
    "--collect-submodules", "src.models",
    "--exclude-module", "tkinter",
    "--exclude-module", "matplotlib",
    "--exclude-module", "numpy",
    "--exclude-module", "pandas",
    "--clean",
    "main.py",
])
```

## 更新说明

每次我修改代码后，你只需要：
1. 确保代码更新完成
2. 运行 `package.bat` 重新打包
3. 新的 `dist/Znote_Win64_v0.1.0_{时间戳}.exe` 就是最新版本

## 文件结构说明

```
项目根目录/
├── package.bat          # 打包脚本 (批处理) - 调用 package.py
├── package.py           # 打包脚本 (Python) - 主打包逻辑
├── package.ps1          # 打包脚本 (PowerShell) - 备用
├── README_PACKAGE打包说明文件.md    # 本说明文件
├── main.py             # 程序入口
├── version.py          # 版本信息文件
├── src/                # 源代码
├── assets/             # 资源文件 (图标等)
├── data/               # 用户数据 (自动生成)
├── build/              # 构建临时文件 (打包时生成)
├── dist/               # 输出文件 (打包后生成)
└── *.spec              # PyInstaller 配置文件 (打包时生成)
```

## 注意事项

- 打包时请关闭程序，避免文件被占用
- 第一次打包时间较长，后续会快一些 (有缓存)
- 生成的 EXE 是独立的，可以复制到其他电脑运行
- 用户数据保存在程序同目录的 `data/` 文件夹中

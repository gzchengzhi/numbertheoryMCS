chcp 65001

REM 1. 清理
del theorem_weights.json
del dependency_records.json
del training_history.json
del debug.txt
rmdir /s /q __pycache__

REM 2. 检查 .gitignore 存在
REM （用上面的内容）

REM 3. 初始化
git init
git add .
git commit -m "Initial release: numbertheoryMCS v0.1

- 概念三角形 + 全互联网络检索层
- 一次性学习（不训练、不迭代）
- 跨谓词、多层嵌套的链式依赖发现
- 自然语言接口（本地 Qwen）
- Web 界面（Flask）"

REM 4. 推到 GitHub
git remote add origin git@github.com:gzchengzhi/numbertheoryMCS.git
git branch -M main
git push -u origin main
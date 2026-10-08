@echo off
chcp 65001 >nul

echo ===== 测试 1 =====
python nl_interface.py --query "证明根号2是无理数"

echo.
echo ===== 测试 2 =====
python nl_interface.py --query "帮我证明一下√5不是有理数" --backend local

echo.
echo ===== 测试 3 =====
python nl_interface.py --query "17是不是质数" --backend local

echo.
echo ===== 测试 4 =====
python nl_interface.py --query "证明素数无穷多" --backend local

pause
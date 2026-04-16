@echo off
echo 正在清理旧文件...
rmdir /s /q build dist 2>nul
del AKShare_Gui.spec 2>nul

echo 正在重新打包...
pyinstaller AKShare_Gui.spec --clean --noconfirm

echo 正在创建发布包...
mkdir release

copy dist\AKShare_Gui.exe release\
copy 打包后配置说明.md release\
copy README.md release\

echo 正在压缩发布包...
powershell -Command "Compress-Archive -Path release\* -DestinationPath AKShare_Release.zip -Force"

echo 发布包创建完成！
echo AKShare_Release.zip
pause
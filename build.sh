#!/bin/zsh
set -eu
src_dir="${0:A:h}"
output_dir="$src_dir/dist"
app_dir="$output_dir/B站字幕助手.app"
mkdir -p "$output_dir"
mkdir -p "$app_dir/Contents/MacOS" "$app_dir/Contents/Resources"
icon_work=$(mktemp -d)
trap 'rm -rf "$icon_work"' EXIT
swift "$src_dir/Icon.swift" "$icon_work/AppIcon.iconset"
iconutil -c icns "$icon_work/AppIcon.iconset" -o "$app_dir/Contents/Resources/AppIcon.icns"
cp "$icon_work/AppIcon.iconset/icon_512x512@2x.png" "$output_dir/AppIcon.png"
swiftc -swift-version 5 -target "$(uname -m)-apple-macosx13.0" -O "$src_dir/App.swift" -o "$app_dir/Contents/MacOS/BiliCaption" -framework SwiftUI -framework AppKit -framework WebKit
cp "$src_dir/extract.py" "$app_dir/Contents/Resources/extract.py"
cp -R "$src_dir/vendor" "$app_dir/Contents/Resources/"
find "$app_dir/Contents/Resources/vendor" -type d -name __pycache__ -prune -exec rm -r {} +
cat > "$app_dir/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>BiliCaption</string>
<key>CFBundleIdentifier</key><string>local.b1ah.bilicaptions</string>
<key>CFBundleName</key><string>B站字幕助手</string>
<key>CFBundleDisplayName</key><string>B站字幕助手</string>
<key>CFBundleIconFile</key><string>AppIcon.icns</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>1.2.0</string>
<key>CFBundleVersion</key><string>1.2.0</string>
<key>LSApplicationCategoryType</key><string>public.app-category.productivity</string>
<key>LSMinimumSystemVersion</key><string>13.0</string>
<key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLIST
codesign --force --sign - "$app_dir"
echo "Built: $app_dir"

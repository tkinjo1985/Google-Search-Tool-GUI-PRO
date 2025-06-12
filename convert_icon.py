#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アイコンファイル変換スクリプト
PNGファイルをICO形式に変換します
"""

from PIL import Image
import os

def convert_png_to_ico():
    """PNGファイルをICOファイルに変換"""
    png_path = "icon/ef811ec4-03df-42a3-b390-3aae2771ebf3.png"
    ico_path = "icon/app_icon.ico"
    
    try:
        # PNGファイルを開く
        with Image.open(png_path) as img:
            # RGBAモードに変換（透明度対応）
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # 複数サイズのICOファイルを作成
            # 一般的なアイコンサイズ: 16x16, 32x32, 48x48, 64x64, 128x128, 256x256
            sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
            
            # 元画像のサイズが大きすぎる場合は256x256にリサイズ
            if img.size[0] > 256 or img.size[1] > 256:
                img = img.resize((256, 256), Image.Resampling.LANCZOS)
            
            # ICOファイルとして保存
            img.save(ico_path, format='ICO', sizes=sizes)
            
            print(f"✅ ICOファイルを作成しました: {ico_path}")
            
            # ファイルサイズを表示
            ico_size = os.path.getsize(ico_path)
            print(f"📊 ICOファイルサイズ: {ico_size:,} bytes ({ico_size/1024:.1f} KB)")
            
    except Exception as e:
        print(f"❌ 変換エラー: {e}")

if __name__ == "__main__":
    convert_png_to_ico()

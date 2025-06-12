#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Search Tool - GUIアプリケーション起動スクリプト
"""

import sys
import os

# プロジェクトのsrcディレクトリをパスに追加
# PyInstallerでEXE化した際の実行パスを考慮
if getattr(sys, 'frozen', False):
    # EXE実行時
    project_root = os.path.dirname(sys.executable)
else:
    # 通常のPython実行時
    project_root = os.path.dirname(os.path.abspath(__file__))

src_path = os.path.join(project_root, 'src')
if os.path.exists(src_path):
    sys.path.insert(0, src_path)


def check_pyqt6():
    """PyQt6がインストールされているかチェック"""
    try:
        import PyQt6
        return True
    except ImportError:
        return False


def main():
    """メイン関数"""
    print("=" * 50)
    print("🔍 Google Search Tool (GUI版)")
    print("=" * 50)
    
    # PyQt6の確認
    if not check_pyqt6():
        print("❌ PyQt6がインストールされていません。")
        print("インストール方法: pip install PyQt6")
        return 1
    
    try:
        print("🖥️  GUIアプリケーションを起動しています...")
        from src.gui_main import main as gui_main
        gui_main()
        return 0
    except Exception as e:
        print(f"❌ アプリケーション起動エラー: {e}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n操作がキャンセルされました。")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 予期しないエラーが発生しました: {e}")
        sys.exit(1)

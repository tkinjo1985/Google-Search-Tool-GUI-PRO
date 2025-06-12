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
    """PyQt6がインストールされているかチェック（遅延インポート）"""
    try:
        import PyQt6
        return True
    except ImportError:
        return False


def check_dependencies():
    """必要な依存関係をチェック（最小限のインポートで最適化）"""
    missing_modules = []
    
    # 重要なモジュールのみチェック
    required_modules = ['PyQt6', 'requests']
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    return missing_modules


def main():
    """メイン関数（起動最適化済み）"""
    print("=" * 50)
    print("🔍 Google Search Tool (GUI版)")
    print("=" * 50)
    
    # 依存関係の確認（最小限）
    missing = check_dependencies()
    if missing:
        print(f"❌ 以下のモジュールがインストールされていません: {', '.join(missing)}")
        print("インストール方法: pip install -r requirements.txt")
        return 1
    
    try:
        print("🖥️  GUIアプリケーションを起動しています...")
        
        # 遅延インポートで起動時間を短縮
        print("📦 モジュール読み込み中...")
        from src.gui_main import main as gui_main
        
        print("✅ 起動準備完了")
        
        # アプリケーション起動
        gui_main()
        return 0
    except Exception as e:
        print(f"❌ アプリケーション起動エラー: {e}")
        import traceback
        traceback.print_exc()
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

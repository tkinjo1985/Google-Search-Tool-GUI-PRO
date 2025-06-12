#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Virtual Table GUI デモテスト
"""

import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt

# プロジェクトパス設定
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from virtual_table_widget import VirtualTableWidget
except ImportError:
    from src.virtual_table_widget import VirtualTableWidget


class VirtualTableDemo(QMainWindow):
    """Virtual Table デモウィンドウ"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Virtual Table デモ")
        self.setGeometry(100, 100, 1200, 700)
        
        # 中央ウィジェット作成
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # ボタンレイアウト
        button_layout = QHBoxLayout()
        
        # テストデータ追加ボタン
        add_small_btn = QPushButton("少量データ追加 (100件)")
        add_small_btn.clicked.connect(lambda: self.add_test_data(100))
        
        add_medium_btn = QPushButton("中量データ追加 (1,000件)")
        add_medium_btn.clicked.connect(lambda: self.add_test_data(1000))
        
        add_large_btn = QPushButton("大量データ追加 (10,000件)")
        add_large_btn.clicked.connect(lambda: self.add_test_data(10000))
        
        clear_btn = QPushButton("データクリア")
        clear_btn.clicked.connect(self.clear_data)
        
        button_layout.addWidget(add_small_btn)
        button_layout.addWidget(add_medium_btn)
        button_layout.addWidget(add_large_btn)
        button_layout.addWidget(clear_btn)
        
        layout.addLayout(button_layout)
        
        # Virtual Table ウィジェット
        self.virtual_table = VirtualTableWidget(
            enable_pagination=True,
            page_size=1000,
            parent=self
        )
        layout.addWidget(self.virtual_table)
        
        # シグナル接続
        self.virtual_table.rowSelected.connect(self.on_row_selected)
        self.virtual_table.dataChanged.connect(self.on_data_changed)
        self.virtual_table.filterChanged.connect(self.on_filter_changed)
        
        print("Virtual Table デモが起動しました")
    
    def add_test_data(self, count: int):
        """テストデータを追加"""
        import time
        start_time = time.time()
        
        print(f"テストデータ {count} 件を追加中...")
        
        test_data = []
        for i in range(count):
            data = {
                'keyword': f'キーワード{i+1}',
                'rank': (i % 100) + 1,
                'title': f'テストタイトル {i+1} - サンプルコンテンツ',
                'url': f'https://example.com/page-{i+1}',
                'snippet': f'これはテストスニペット {i+1} です。検索結果のサンプルテキストを表示しています。',
                'timestamp': f'2025-06-13 {10 + (i % 14):02d}:{(i * 3) % 60:02d}:00'
            }
            test_data.append(data)
        
        self.virtual_table.setData(test_data)
        
        elapsed_time = time.time() - start_time
        print(f"✅ {count} 件のデータ追加完了 (所要時間: {elapsed_time:.3f}秒)")
    
    def clear_data(self):
        """データをクリア"""
        self.virtual_table.clearData()
        print("データがクリアされました")
    
    def on_row_selected(self, row: int, data: dict):
        """行選択時のイベント"""
        print(f"行選択: {row}, キーワード: {data.get('keyword', 'N/A')}")
    
    def on_data_changed(self, row_count: int):
        """データ変更時のイベント"""
        print(f"データ変更: 総行数 {row_count}")
    
    def on_filter_changed(self, filter_text: str, result_count: int):
        """フィルタ変更時のイベント"""
        print(f"フィルタ変更: '{filter_text}', 結果 {result_count} 件")


def main():
    """メイン関数"""
    app = QApplication(sys.argv)
      # ハイDPI対応（PyQt6では不要、自動対応）
    # app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    # app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    
    demo = VirtualTableDemo()
    demo.show()
    
    print("Virtual Table デモを起動中...")
    print("操作:")
    print("- ボタンをクリックしてテストデータを追加")
    print("- フィルタバーで検索結果をフィルタリング")
    print("- 行をクリックして選択")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

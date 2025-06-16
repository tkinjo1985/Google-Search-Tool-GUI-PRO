#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Virtual Table 機能のテスト
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# テスト対象モジュールのパスを設定
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# テスト用のQApplication
app = None

def setUpModule():
    """モジュール設定"""
    global app
    if QApplication.instance() is None:
        app = QApplication([])

def tearDownModule():
    """モジュールクリーンアップ"""
    global app
    if app is not None:
        app.quit()


class TestVirtualTableModel(unittest.TestCase):
    """Virtual Table Model のテストクラス"""
    
    def setUp(self):
        """テスト前の設定"""
        from virtual_table_model import VirtualTableModel
        self.model = VirtualTableModel()
        
        # テスト用データ
        self.test_data = [
            {
                'keyword': 'test1',
                'rank': 1,
                'title': 'Test Title 1',
                'url': 'https://example.com/1',
                'snippet': 'Test snippet 1',
                'timestamp': '2025-06-13 10:00:00'
            },
            {
                'keyword': 'test2',
                'rank': 2,
                'title': 'Test Title 2',
                'url': 'https://example.com/2',
                'snippet': 'Test snippet 2',
                'timestamp': '2025-06-13 10:01:00'
            }
        ]
    
    def test_initial_state(self):
        """初期状態のテスト"""
        self.assertEqual(self.model.rowCount(), 0)
        self.assertEqual(self.model.columnCount(), 6)
        self.assertEqual(self.model.getResultCount(), 0)
    
    def test_set_data(self):
        """データ設定のテスト"""
        self.model.setData(self.test_data)
        
        self.assertEqual(self.model.rowCount(), 2)
        self.assertEqual(self.model.getResultCount(), 2)
        
        # データ取得テスト
        result = self.model.getResult(0)
        self.assertEqual(result['keyword'], 'test1')
        self.assertEqual(result['title'], 'Test Title 1')
    
    def test_add_result(self):
        """単一結果追加のテスト"""
        self.model.addResult(self.test_data[0])
        
        self.assertEqual(self.model.rowCount(), 1)
        self.assertEqual(self.model.getResultCount(), 1)
        
        result = self.model.getResult(0)
        self.assertEqual(result['keyword'], 'test1')
    
    def test_add_multiple_results(self):
        """複数結果追加のテスト"""
        self.model.addResults(self.test_data)
        
        self.assertEqual(self.model.rowCount(), 2)
        self.assertEqual(self.model.getResultCount(), 2)
    
    def test_clear_data(self):
        """データクリアのテスト"""
        self.model.setData(self.test_data)
        self.assertEqual(self.model.rowCount(), 2)
        
        self.model.clearData()
        self.assertEqual(self.model.rowCount(), 0)
        self.assertEqual(self.model.getResultCount(), 0)
    
    def test_data_retrieval(self):
        """データ取得のテスト"""
        self.model.setData(self.test_data)
        
        # インデックスでのデータ取得
        index = self.model.index(0, 0)  # キーワード列
        value = self.model.data(index, Qt.ItemDataRole.DisplayRole)
        self.assertEqual(value, 'test1')
        
        index = self.model.index(0, 2)  # タイトル列
        value = self.model.data(index, Qt.ItemDataRole.DisplayRole)
        self.assertEqual(value, 'Test Title 1')
    
    def test_header_data(self):
        """ヘッダーデータのテスト"""
        headers = ["キーワード", "順位", "タイトル", "URL", "スニペット", "検索時刻"]
        
        for i, expected_header in enumerate(headers):
            header = self.model.headerData(i, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
            self.assertEqual(header, expected_header)
    
    def test_sort(self):
        """ソート機能のテスト"""
        # ソート用のテストデータ
        sort_data = [
            {'keyword': 'zzz', 'rank': 3, 'title': 'C', 'url': '', 'snippet': '', 'timestamp': ''},
            {'keyword': 'aaa', 'rank': 1, 'title': 'A', 'url': '', 'snippet': '', 'timestamp': ''},
            {'keyword': 'mmm', 'rank': 2, 'title': 'B', 'url': '', 'snippet': '', 'timestamp': ''}
        ]
        
        self.model.setData(sort_data)
        
        # キーワード列（0列目）で昇順ソート
        self.model.sort(0, Qt.SortOrder.AscendingOrder)
        
        first_keyword = self.model.getResult(0)['keyword']
        self.assertEqual(first_keyword, 'aaa')
        
        # 順位列（1列目）で降順ソート
        self.model.sort(1, Qt.SortOrder.DescendingOrder)
        
        first_rank = self.model.getResult(0)['rank']
        self.assertEqual(first_rank, 3)


class TestFilterableVirtualTableModel(unittest.TestCase):
    """Filterable Virtual Table Model のテストクラス"""
    
    def setUp(self):
        """テスト前の設定"""
        from virtual_table_model import FilterableVirtualTableModel
        self.model = FilterableVirtualTableModel()
        
        # テスト用データ
        self.test_data = [
            {
                'keyword': 'python programming',
                'rank': 1,
                'title': 'Python Tutorial',
                'url': 'https://python.org',
                'snippet': 'Learn Python programming',
                'timestamp': '2025-06-13 10:00:00'
            },
            {
                'keyword': 'java development',
                'rank': 1,
                'title': 'Java Guide',
                'url': 'https://java.com',
                'snippet': 'Java development guide',
                'timestamp': '2025-06-13 10:01:00'
            },
            {
                'keyword': 'web development',
                'rank': 1,
                'title': 'Web Dev Tutorial',
                'url': 'https://webdev.com',
                'snippet': 'Learn web development',
                'timestamp': '2025-06-13 10:02:00'
            }
        ]
        
        self.model.setData(self.test_data)
    
    def test_no_filter(self):
        """フィルタなしのテスト"""
        self.assertEqual(self.model.rowCount(), 3)
        self.assertEqual(self.model.getFilteredCount(), 3)
    
    def test_keyword_filter(self):
        """キーワードフィルタのテスト"""
        # "python"でフィルタ
        self.model.setFilter("python")
        
        self.assertEqual(self.model.rowCount(), 1)
        self.assertEqual(self.model.getFilteredCount(), 1)
        
        # フィルタ結果の確認
        index = self.model.index(0, 0)
        value = self.model.data(index, Qt.ItemDataRole.DisplayRole)
        self.assertEqual(value, 'python programming')
    
    def test_title_filter(self):
        """タイトルフィルタのテスト"""
        # "tutorial"でフィルタ
        self.model.setFilter("tutorial")
        
        self.assertEqual(self.model.rowCount(), 2)  # Python Tutorial, Web Dev Tutorial
        self.assertEqual(self.model.getFilteredCount(), 2)
    
    def test_case_insensitive_filter(self):
        """大文字小文字を区別しないフィルタのテスト"""
        # 大文字で検索
        self.model.setFilter("PYTHON")
        
        self.assertEqual(self.model.rowCount(), 1)
        self.assertEqual(self.model.getFilteredCount(), 1)
    
    def test_clear_filter(self):
        """フィルタクリアのテスト"""
        # フィルタ適用
        self.model.setFilter("python")
        self.assertEqual(self.model.rowCount(), 1)
        
        # フィルタクリア
        self.model.clearFilter()
        self.assertEqual(self.model.rowCount(), 3)
        self.assertEqual(self.model.getFilteredCount(), 3)
    
    def test_no_match_filter(self):
        """マッチしないフィルタのテスト"""
        self.model.setFilter("nonexistent")
        
        self.assertEqual(self.model.rowCount(), 0)
        self.assertEqual(self.model.getFilteredCount(), 0)
    
    def test_add_result_with_filter(self):
        """フィルタ適用中の結果追加のテスト"""
        # フィルタ適用
        self.model.setFilter("python")
        self.assertEqual(self.model.rowCount(), 1)
        
        # 新しい結果を追加
        new_result = {
            'keyword': 'python advanced',
            'rank': 1,
            'title': 'Advanced Python',
            'url': 'https://python-advanced.com',
            'snippet': 'Advanced Python techniques',
            'timestamp': '2025-06-13 10:03:00'
        }
        
        self.model.addResult(new_result)
        
        # フィルタにマッチするので表示される
        self.assertEqual(self.model.rowCount(), 2)
        self.assertEqual(self.model.getFilteredCount(), 2)


class TestVirtualTableWidget(unittest.TestCase):
    """Virtual Table Widget のテストクラス"""
    
    def setUp(self):
        """テスト前の設定"""
        from virtual_table_widget import VirtualTableWidget
        self.widget = VirtualTableWidget()
        
        # テスト用データ
        self.test_data = [
            {
                'keyword': 'test1',
                'rank': 1,
                'title': 'Test Title 1',
                'url': 'https://example.com/1',
                'snippet': 'Test snippet 1',
                'timestamp': '2025-06-13 10:00:00'
            },
            {
                'keyword': 'test2',
                'rank': 2,
                'title': 'Test Title 2',
                'url': 'https://example.com/2',
                'snippet': 'Test snippet 2',
                'timestamp': '2025-06-13 10:01:00'
            }
        ]
    
    def test_initial_state(self):
        """初期状態のテスト"""
        self.assertEqual(self.widget.getResultCount(), 0)
        self.assertEqual(self.widget.getFilteredCount(), 0)
    
    def test_set_data(self):
        """データ設定のテスト"""
        self.widget.setData(self.test_data)
        
        self.assertEqual(self.widget.getResultCount(), 2)
        self.assertEqual(self.widget.getFilteredCount(), 2)
    
    def test_add_result(self):
        """結果追加のテスト"""
        self.widget.addResult(self.test_data[0])
        
        self.assertEqual(self.widget.getResultCount(), 1)
        self.assertEqual(self.widget.getFilteredCount(), 1)
    
    def test_add_multiple_results(self):
        """複数結果追加のテスト"""
        self.widget.addResults(self.test_data)
        
        self.assertEqual(self.widget.getResultCount(), 2)
        self.assertEqual(self.widget.getFilteredCount(), 2)
    
    def test_clear_data(self):
        """データクリアのテスト"""
        self.widget.setData(self.test_data)
        self.assertEqual(self.widget.getResultCount(), 2)
        
        self.widget.clearData()
        self.assertEqual(self.widget.getResultCount(), 0)
        self.assertEqual(self.widget.getFilteredCount(), 0)
    
    def test_filter_functionality(self):
        """フィルタ機能のテスト"""
        self.widget.setData(self.test_data)
        
        # フィルタ適用
        self.widget.setFilter("test1")
        self.assertEqual(self.widget.getFilteredCount(), 1)
        
        # フィルタクリア
        self.widget.clearFilter()
        self.assertEqual(self.widget.getFilteredCount(), 2)
    
    def test_get_data(self):
        """データ取得のテスト"""
        self.widget.setData(self.test_data)
        
        data = self.widget.getData()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['keyword'], 'test1')
        self.assertEqual(data[1]['keyword'], 'test2')
    
    def test_export_data(self):
        """エクスポートデータのテスト"""
        self.widget.setData(self.test_data)
        
        # フィルタなし
        export_data = self.widget.exportData()
        self.assertEqual(len(export_data), 2)
        
        # フィルタあり
        self.widget.setFilter("test1")
        export_data = self.widget.exportData()
        self.assertEqual(len(export_data), 1)
        self.assertEqual(export_data[0]['keyword'], 'test1')
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.widget.deleteLater()


class TestVirtualTablePerformance(unittest.TestCase):
    """Virtual Table パフォーマンステスト"""
    def setUp(self):
        """テスト前の設定"""
        from virtual_table_widget import VirtualTableWidget
        self.widget = VirtualTableWidget()
    
    def test_large_dataset_performance(self):
        """大量データのパフォーマンステスト"""
        import time
        
        # 大量のテストデータを生成
        large_data = []
        for i in range(10000):
            large_data.append({
                'keyword': f'keyword_{i}',
                'rank': i % 10 + 1,
                'title': f'Title {i}',
                'url': f'https://example.com/{i}',
                'snippet': f'Snippet for item {i}',
                'timestamp': f'2025-06-13 10:{i%60:02d}:00'
            })
        
        # データ設定の時間測定
        start_time = time.time()
        self.widget.setData(large_data)
        set_time = time.time() - start_time
        
        # データ設定は1秒以内で完了すべき
        self.assertLess(set_time, 1.0, f"Data setting took {set_time:.3f} seconds")
        
        # 結果数確認
        self.assertEqual(self.widget.getResultCount(), 10000)
        
        # フィルタのパフォーマンステスト
        start_time = time.time()
        self.widget.setFilter("keyword_100")
        filter_time = time.time() - start_time
        
        # フィルタは0.5秒以内で完了すべき
        self.assertLess(filter_time, 0.5, f"Filtering took {filter_time:.3f} seconds")
        
        # フィルタ結果確認
        filtered_count = self.widget.getFilteredCount()
        self.assertGreater(filtered_count, 0)
        self.assertLess(filtered_count, 1000)  # 部分マッチなので複数該当
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.widget.deleteLater()


if __name__ == '__main__':
    # すべてのテストを実行
    unittest.main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統合テスト
実際のGoogle API使用テスト、エンドツーエンドテスト、パフォーマンステスト
"""

import unittest
import tempfile
import os
import sys
import time
import csv
from unittest.mock import patch, Mock
import requests

# プロジェクトのsrcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.search_tool import SearchTool
from src.config_manager import ConfigManager
from src.google_search_api import GoogleSearchAPI, APIError
from src.search_engine import SearchEngine
from src.csv_writer import CSVWriter
from src.search_result import SearchResult


class TestIntegration(unittest.TestCase):
    """統合テストクラス"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        
        # テスト用設定を作成
        self.test_config = {
            "google_api": {
                "api_key": "test_api_key",
                "custom_search_engine_id": "test_engine_id"
            },
            "output": {
                "directory": self.temp_dir,
                "filename_prefix": "integration_test"
            },
            "logging": {
                "level": "ERROR",  # テスト中はエラーログのみ
                "file_path": os.path.join(self.temp_dir, "test.log"),
                "console_output": False
            },
            "search": {
                "retry_count": 2,
                "retry_delay": 0.1,
                "timeout": 5
            }
        }
        
        self.config_file = os.path.join(self.temp_dir, 'test_config.json')
        
        # 設定ファイルを保存
        import json
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_config, f, ensure_ascii=False, indent=2)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_end_to_end_mock_api(self):
        """エンドツーエンドテスト（モックAPI使用）"""
        # モックAPIレスポンスを作成
        mock_response = {
            "items": [
                {
                    "title": "Python プログラミング入門",
                    "link": "https://example.com/python",
                    "snippet": "Pythonプログラミングの基礎を学ぼう",
                    "displayLink": "example.com",
                    "formattedUrl": "https://example.com/python"
                }
            ],
            "searchInformation": {
                "totalResults": "1"
            }
        }
        
        # GoogleSearchAPIクラス全体をモック
        with patch('src.google_search_api.GoogleSearchAPI') as mock_api_class:
            # モックAPIインスタンスを作成
            mock_api_instance = Mock()
            mock_api_instance.search.return_value = mock_response
            mock_api_instance.validate_connection.return_value = True
            mock_api_class.return_value = mock_api_instance
            
            # モック設定を作成
            mock_config = self._create_mock_config()
            
            # SearchToolを初期化
            search_tool = SearchTool()
            search_tool.initialize_for_test(mock_config)
            
            # 検索を実行
            keywords = ["Python プログラミング"]
            results = search_tool.run_search(keywords)
            
            # 結果を確認
            self.assertEqual(len(results), 1)
            result = results[0]
            self.assertEqual(result.title, "Python プログラミング入門")
            self.assertEqual(result.url, "https://example.com/python")
            self.assertEqual(result.search_query, "Python プログラミング")
            
            # CSVファイルが作成されていることを確認
            csv_files = [f for f in os.listdir(self.temp_dir) if f.endswith('.csv')]
            self.assertGreater(len(csv_files), 0)
    
    def test_error_handling_integration(self):
        """エラーハンドリング統合テスト"""
        # GoogleSearchAPIクラス全体をモック
        with patch('src.search_engine.GoogleSearchAPI') as mock_api_class:
            # モックAPIインスタンスを作成
            mock_api_instance = Mock()
            mock_api_instance.search.side_effect = requests.exceptions.ConnectionError("Connection failed")
            mock_api_class.return_value = mock_api_instance
            
            mock_config = self._create_mock_config()
            
            search_tool = SearchTool()
            search_tool.initialize_for_test(mock_config)
            
            # 検索を実行（エラーが発生するはず）
            keywords = ["テストクエリ"]
            results = search_tool.run_search(keywords)
            
            # 失敗したキーワードが記録されることを確認
            self.assertEqual(len(search_tool.failed_keywords), 1)
            self.assertEqual(len(results), 0)
    
    def test_multiple_keywords_processing(self):
        """複数キーワード処理テスト"""
        # SearchEngineを直接モック
        with patch('src.google_search_api.GoogleSearchAPI') as mock_api_class:
            # モック検索エンジンインスタンスを作成
            mock_api_instance = Mock()
            
            # 各キーワードに対してモック結果を設定
            def mock_search_func(query):
                return {
                    "items": [
                        {
                            "title": f"結果{query[-1]}",
                            "link": f"https://example{query[-1]}.com",
                            "snippet": f"テスト結果{query[-1]}",
                            "displayLink": f"example{query[-1]}.com",
                            "formattedUrl": f"https://example{query[-1]}.com"
                        }
                    ]
                }
            
            mock_api_instance.search.side_effect = mock_search_func
            mock_api_instance.validate_connection.return_value = True
            mock_api_class.return_value = mock_api_instance
            
            mock_config = self._create_mock_config()
            
            search_tool = SearchTool()
            search_tool.initialize_for_test(mock_config)
            
            # 複数キーワードで検索を実行
            keywords = [f"クエリ{i}" for i in range(5)]
            results = search_tool.run_search(keywords)
            
            # 全ての検索が成功することを確認
            self.assertEqual(len(results), 5)
            self.assertEqual(len(search_tool.failed_keywords), 0)
    
    def test_partial_failure_handling(self):
        """部分失敗処理テスト"""
        # 一部成功、一部失敗のシナリオ
        responses_and_errors = [
            {"items": [{"title": "成功1", "link": "https://example1.com", "snippet": "成功"}]},
            requests.exceptions.ConnectionError("失敗"),
            {"items": [{"title": "成功2", "link": "https://example2.com", "snippet": "成功"}]},
            requests.exceptions.Timeout("タイムアウト"),
        ]
        
        # GoogleSearchAPIクラス全体をモック
        with patch('src.search_engine.GoogleSearchAPI') as mock_api_class:
            # モックAPIインスタンスを作成
            mock_api_instance = Mock()
            mock_api_instance.search.side_effect = responses_and_errors
            mock_api_class.return_value = mock_api_instance
            
            mock_config = self._create_mock_config()
            
            search_tool = SearchTool()
            search_tool.initialize_for_test(mock_config)
            
            keywords = ["成功1", "失敗1", "成功2", "失敗2"]
            results = search_tool.run_search(keywords)
            
            # 部分的な成功と失敗を確認
            self.assertEqual(len(results), 2)
            self.assertEqual(len(search_tool.failed_keywords), 2)
    
    def test_csv_output_integration(self):
        """CSV出力統合テスト"""
        # GoogleSearchAPIクラス全体をモック
        with patch('src.google_search_api.GoogleSearchAPI') as mock_api_class:
            # モック検索エンジンインスタンスを作成
            mock_api_instance = Mock()
            mock_response = {
                "items": [
                    {
                        "title": "統合テスト結果",
                        "link": "https://integration-test.com",
                        "snippet": "これは統合テストの結果です",
                        "displayLink": "integration-test.com",
                        "formattedUrl": "https://integration-test.com"
                    }
                ]
            }
            mock_api_instance.search.return_value = mock_response
            mock_api_instance.validate_connection.return_value = True
            mock_api_class.return_value = mock_api_instance
            
            mock_config = self._create_mock_config()
            
            search_tool = SearchTool()
            search_tool.initialize_for_test(mock_config)
            
            keywords = ["統合テスト"]
            results = search_tool.run_search(keywords)
            
            # 結果を確認
            self.assertEqual(len(results), 1)
            self.assertEqual(len(search_tool.failed_keywords), 0)
            
            # CSVファイルが作成されていることを確認
            csv_files = [f for f in os.listdir(self.temp_dir) if f.endswith('.csv')]
            self.assertGreater(len(csv_files), 0)
            
            # CSVファイルの内容を確認
            csv_file = os.path.join(self.temp_dir, csv_files[0])
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]['タイトル'], "統合テスト結果")
                self.assertEqual(rows[0]['URL'], "https://integration-test.com")
    
    def test_performance_multiple_searches(self):
        """パフォーマンステスト（複数検索）"""
        # 10個のキーワードで検索時間を測定
        mock_response = {
            "items": [
                {
                    "title": "パフォーマンステスト",
                    "link": "https://performance-test.com",
                    "snippet": "パフォーマンステスト結果"
                }
            ]
        }
        
        # GoogleSearchAPIクラス全体をモック
        with patch('src.google_search_api.GoogleSearchAPI') as mock_api_class:
            # モックAPIインスタンスを作成
            mock_api_instance = Mock()
            mock_api_instance.search.return_value = mock_response
            mock_api_instance.validate_connection.return_value = True
            mock_api_class.return_value = mock_api_instance
            
            mock_config = self._create_mock_config()
            
            search_tool = SearchTool()
            search_tool.initialize_for_test(mock_config)
            
            # 10個のキーワードで検索
            keywords = [f"パフォーマンステスト{i}" for i in range(10)]
            
            start_time = time.time()
            results = search_tool.run_search(keywords)
            end_time = time.time()
            
            execution_time = end_time - start_time
            
            # 実行時間が妥当であることを確認（10秒以内）
            self.assertLess(execution_time, 10.0)
            
            # 全ての検索が成功することを確認
            self.assertEqual(len(results), 10)
    
    def test_interrupt_handling(self):
        """割り込み処理テスト"""
        # 長時間の検索中に割り込みが発生するシナリオ
        def slow_search(*args, **kwargs):
            time.sleep(0.1)  # 短い遅延をシミュレート
            return {"items": [{"title": "遅い検索", "link": "https://slow.com", "snippet": "遅い"}]}
        
        # GoogleSearchAPIクラス全体をモック
        with patch('src.google_search_api.GoogleSearchAPI') as mock_api_class:
            # モックAPIインスタンスを作成
            mock_api_instance = Mock()
            mock_api_instance.search.side_effect = slow_search
            mock_api_instance.validate_connection.return_value = True
            mock_api_class.return_value = mock_api_instance
            
            mock_config = self._create_mock_config()
            
            search_tool = SearchTool()
            search_tool.initialize_for_test(mock_config)
            
            # 大量のキーワードを準備
            keywords = [f"キーワード{i}" for i in range(100)]
            
            # 少し検索を実行してから割り込み
            def interrupt_after_delay():
                time.sleep(0.05)
                search_tool.interrupted = True
            
            import threading
            interrupt_thread = threading.Thread(target=interrupt_after_delay)
            interrupt_thread.start()
            
            results = search_tool.run_search(keywords)
            interrupt_thread.join()
            
            # 割り込み後に部分的な結果が保存されていることを確認
            total_processed = len(results) + len(search_tool.failed_keywords)
            self.assertLess(total_processed, len(keywords))  # 全部は処理されていない
            self.assertGreater(total_processed, 0)  # 何かは処理されている
    
    def test_large_dataset_processing(self):
        """大きなデータセット処理テスト"""
        # 50個のキーワードで処理
        mock_response = {
            "items": [
                {
                    "title": "大規模テスト",
                    "link": "https://large-test.com",
                    "snippet": "大規模テスト結果"
                }
            ]
        }
        
        with patch('src.google_search_api.GoogleSearchAPI') as mock_api_class:
            # モックAPIインスタンスを作成
            mock_api_instance = Mock()
            mock_api_instance.search.return_value = mock_response
            mock_api_instance.validate_connection.return_value = True
            mock_api_class.return_value = mock_api_instance
            
            mock_config = self._create_mock_config()
            
            search_tool = SearchTool()
            search_tool.initialize_for_test(mock_config)
            
            # 50個のキーワード
            keywords = [f"大規模テスト{i}" for i in range(50)]
            results = search_tool.run_search(keywords)
            
            # 全ての検索が完了することを確認
            self.assertEqual(len(results), 50)
            
            # CSVファイルが作成され、全てのデータが含まれていることを確認
            csv_files = [f for f in os.listdir(self.temp_dir) if f.endswith('.csv')]
            self.assertGreater(len(csv_files), 0)
            
            csv_file = os.path.join(self.temp_dir, csv_files[0])
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                self.assertEqual(len(rows), 50)
    
    def _create_mock_config(self):
        """モック設定オブジェクトを作成"""
        mock_config = Mock()
        mock_config.get_google_api_key.return_value = "test_key"
        mock_config.get_search_engine_id.return_value = "test_id"
        mock_config.get_output_directory.return_value = self.temp_dir
        mock_config.get_filename_prefix.return_value = "test"
        mock_config.get_log_level.return_value = "ERROR"
        mock_config.get_log_file_path.return_value = os.path.join(self.temp_dir, "test.log")
        mock_config.get_console_output.return_value = False
        mock_config.get_retry_count.return_value = 2
        mock_config.get_retry_delay.return_value = 0.1
        mock_config.get_timeout.return_value = 5
        return mock_config


class TestErrorScenarios(unittest.TestCase):
    """エラーシナリオテストクラス"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_network_error_scenarios(self):
        """ネットワークエラーシナリオテスト"""
        api = GoogleSearchAPI("test_key", "test_id", retry_count=1, retry_delay=0.01)
        
        # 各種ネットワークエラーをテスト
        network_errors = [
            requests.exceptions.ConnectionError("接続エラー"),
            requests.exceptions.Timeout("タイムアウト"),
            requests.exceptions.RequestException("リクエストエラー"),
        ]
        
        for error in network_errors:
            with self.subTest(error=type(error).__name__):
                with patch('requests.Session.get') as mock_get:
                    mock_get.side_effect = error
                    
                    with self.assertRaises(APIError):
                        api.search("テストクエリ")
    
    def test_api_quota_exceeded(self):
        """API制限超過テスト"""
        api = GoogleSearchAPI("test_key", "test_id", retry_count=1)
        
        # 429 Too Many Requestsエラーをシミュレート
        with patch('requests.Session.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("429")
            mock_get.return_value = mock_response
            
            with self.assertRaises(APIError):
                api.search("テストクエリ")
    
    def test_invalid_api_credentials(self):
        """無効なAPI認証情報テスト"""
        api = GoogleSearchAPI("invalid_key", "invalid_id", retry_count=1)
        
        # 403 Forbiddenエラーをシミュレート
        with patch('requests.Session.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 403
            mock_response.json.return_value = {"error": {"message": "API key not valid"}}
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("403 Client Error: Forbidden")
            mock_get.return_value = mock_response
            
            with self.assertRaises(APIError) as context:
                api.search("テストクエリ")
            
            # エラーメッセージが含まれていることを確認
            self.assertIn("API key not valid", str(context.exception))


if __name__ == '__main__':
    unittest.main()

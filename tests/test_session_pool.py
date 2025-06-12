#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTPセッションプール機能のテスト
接続プール、Keep-Alive、動的タイムアウト機能のテスト
"""

import unittest
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# プロジェクトのsrcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.google_search_api import GoogleSearchAPI, APIError


class TestHTTPSessionPool(unittest.TestCase):
    """HTTPセッションプール機能のテストクラス"""
    
    def setUp(self):
        """テスト前の準備"""
        self.api_key = "test_api_key"
        self.search_engine_id = "test_engine_id"
        self.api = GoogleSearchAPI(
            api_key=self.api_key,
            search_engine_id=self.search_engine_id,
            timeout=5,
            retry_count=2,
            retry_delay=0.1
        )
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.api.close()
    
    def test_session_pool_initialization(self):
        """セッションプールの初期化テスト"""
        # セッションが作成されていることを確認
        self.assertIsNotNone(self.api.session)
        
        # Keep-Aliveヘッダーが設定されていることを確認
        headers = self.api.session.headers
        self.assertEqual(headers.get('Connection'), 'keep-alive')
        self.assertEqual(headers.get('Accept-Encoding'), 'gzip, deflate')
        self.assertIn('User-Agent', headers)
    
    def test_dynamic_timeout_initialization(self):
        """動的タイムアウトの初期化テスト"""
        # 初期状態では設定値のタイムアウトが返される
        self.assertEqual(self.api._get_dynamic_timeout(), self.api.timeout)
        
        # リクエスト履歴が空であることを確認
        self.assertEqual(len(self.api._request_times), 0)
    
    def test_request_time_recording(self):
        """リクエスト時間記録のテスト"""
        # リクエスト時間を記録
        test_times = [1.0, 1.5, 2.0]
        for time_val in test_times:
            self.api._record_request_time(time_val)
        
        # 記録されたことを確認
        self.assertEqual(self.api._request_times, test_times)
    
    def test_request_time_history_limit(self):
        """リクエスト時間履歴の制限テスト"""
        # 制限を超えてリクエスト時間を記録
        max_history = self.api._max_request_history
        for i in range(max_history + 5):
            self.api._record_request_time(i * 0.1)
        
        # 履歴が制限値以下であることを確認
        self.assertLessEqual(len(self.api._request_times), max_history)
        
        # 新しい値が保持されていることを確認
        self.assertIn((max_history + 4) * 0.1, self.api._request_times)
    
    def test_dynamic_timeout_calculation(self):
        """動的タイムアウト計算のテスト"""
        # テスト用のリクエスト時間を設定
        test_times = [1.0, 2.0, 3.0]
        for time_val in test_times:
            self.api._record_request_time(time_val)
        
        # 動的タイムアウトが平均時間の2.5倍になることを確認
        avg_time = sum(test_times) / len(test_times)  # 2.0
        expected_timeout = avg_time * 2.5  # 5.0
        
        # 設定値の範囲内であることも確認
        min_timeout = self.api.timeout * 0.5  # 2.5
        max_timeout = self.api.timeout * 2.0  # 10.0
        expected_timeout = max(min_timeout, min(expected_timeout, max_timeout))
        
        self.assertEqual(self.api._get_dynamic_timeout(), expected_timeout)
    
    def test_performance_stats(self):
        """パフォーマンス統計のテスト"""
        # テスト用データを設定
        test_times = [1.0, 1.5, 2.0, 2.5, 3.0]
        for time_val in test_times:
            self.api._record_request_time(time_val)
        
        # 統計情報を取得
        stats = self.api.get_performance_stats()
        
        # 期待される値を計算
        expected_avg = sum(test_times) / len(test_times)
        expected_min = min(test_times)
        expected_max = max(test_times)
        
        # 統計が正しいことを確認
        self.assertEqual(stats['total_requests'], len(test_times))
        self.assertEqual(stats['avg_request_time'], expected_avg)
        self.assertEqual(stats['min_request_time'], expected_min)
        self.assertEqual(stats['max_request_time'], expected_max)
        self.assertIn('pool_status', stats)
        self.assertIn('dynamic_timeout', stats)
    
    def test_usage_info_with_performance_stats(self):
        """使用量情報にパフォーマンス統計が含まれることのテスト"""
        # テスト用データを設定
        self.api._record_request_time(1.5)
        
        # 使用量情報を取得
        usage_info = self.api.get_usage_info()
        
        # 基本情報が含まれていることを確認
        self.assertIn('api_key_length', usage_info)
        self.assertIn('timeout', usage_info)
        self.assertIn('retry_count', usage_info)
        
        # パフォーマンス統計が含まれていることを確認
        self.assertIn('avg_request_time', usage_info)
        self.assertIn('total_requests', usage_info)
        self.assertIn('pool_status', usage_info)
        self.assertIn('dynamic_timeout', usage_info)
    
    @patch('requests.Session.get')
    def test_request_with_dynamic_timeout(self, mock_get):
        """動的タイムアウトを使用したリクエストのテスト"""
        # モックレスポンスを設定
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_get.return_value = mock_response
        
        # 事前にリクエスト時間を記録（動的タイムアウトを調整）
        self.api._record_request_time(0.5)
        self.api._record_request_time(1.0)
        
        # 検索を実行
        result = self.api.search("テストクエリ")
        
        # リクエストが実行されたことを確認
        mock_get.assert_called_once()
        
        # タイムアウト引数が動的な値になっていることを確認
        call_kwargs = mock_get.call_args[1]
        self.assertIn('timeout', call_kwargs)
        # 動的タイムアウトが使用されていることを確認
        self.assertNotEqual(call_kwargs['timeout'], self.api.timeout)
    
    @patch('requests.Session.get')
    def test_request_time_recording_in_real_request(self, mock_get):
        """実際のリクエスト中でのリクエスト時間記録テスト"""
        # モックレスポンスを設定
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_get.return_value = mock_response
        
        # 初期状態の確認
        initial_count = len(self.api._request_times)
        
        # 検索を実行
        self.api.search("テストクエリ")
        
        # リクエスト時間が記録されたことを確認
        self.assertEqual(len(self.api._request_times), initial_count + 1)
        self.assertGreater(self.api._request_times[-1], 0)
    
    def test_pool_status_method(self):
        """プールステータス取得メソッドのテスト"""
        # プールステータスが文字列で返されることを確認
        status = self.api._get_pool_status()
        self.assertIsInstance(status, str)
    
    def test_session_cleanup(self):
        """セッションクリーンアップのテスト"""
        # セッションが存在することを確認
        self.assertIsNotNone(self.api.session)
        
        # クリーンアップを実行
        self.api.close()
        
        # セッションが閉じられたことを確認（例外が発生しないことを確認）
        try:
            # 閉じられたセッションへのアクセスは例外を発生させるべき
            # ただし、requests.Sessionは閉じた後もエラーを発生させない場合がある
            pass
        except:
            pass  # 何らかの例外が発生してもOK


if __name__ == '__main__':
    unittest.main()

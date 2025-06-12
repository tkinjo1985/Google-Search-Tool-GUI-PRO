#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API接続テスト
GoogleSearchAPIクラスのモックAPI使用テスト、エラーレスポンステスト、リトライ処理テスト
"""

import unittest
import requests
import json
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# プロジェクトのsrcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.google_search_api import GoogleSearchAPI, APIError, RateLimitError


class TestGoogleSearchAPI(unittest.TestCase):
    """GoogleSearchAPIのテストクラス"""
    
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
    
    def test_successful_search(self):
        """正常な検索のテスト"""
        # モックレスポンスを作成
        mock_response = {
            "items": [
                {
                    "title": "テストタイトル",
                    "link": "https://example.com",
                    "snippet": "テストスニペット",
                    "displayLink": "example.com",
                    "formattedUrl": "https://example.com"
                }
            ],
            "searchInformation": {
                "totalResults": "1"
            }
        }
        
        # requests.getをモック
        with patch('requests.Session.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status.return_value = None
            
            # 検索を実行
            result = self.api.search("テストクエリ")
            
            # 結果を確認
            self.assertIn("items", result)
            self.assertEqual(len(result["items"]), 1)
            self.assertEqual(result["items"][0]["title"], "テストタイトル")
            
            # APIが正しく呼び出されたことを確認
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            # 位置引数として渡されたURLをチェック
            url = call_args[0][0] if call_args[0] else ""
            self.assertIn("q=%E3%83%86%E3%82%B9%E3%83%88%E3%82%AF%E3%82%A8%E3%83%AA", url)  # URLエンコード済み
            self.assertIn(f"key={self.api_key}", url)
            self.assertIn(f"cx={self.search_engine_id}", url)
    
    def test_api_key_validation(self):
        """APIキー検証のテスト"""
        # 正常なレスポンス
        mock_response = {
            "items": [],
            "searchInformation": {
                "totalResults": "0"
            }
        }
        
        with patch('requests.Session.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status.return_value = None
            
            # APIキー検証
            is_valid = self.api.validate_api_key()
            self.assertTrue(is_valid)
    
    def test_api_key_validation_failure(self):
        """APIキー検証失敗のテスト"""
        with patch('requests.Session.get') as mock_get:
            # 403エラーレスポンス
            mock_get.return_value.status_code = 403
            mock_get.return_value.json.return_value = {
                "error": {"message": "API key invalid"}
            }
            mock_get.return_value.content = b'{"error": {"message": "API key invalid"}}'
            
            # APIキー検証が失敗することを確認
            is_valid = self.api.validate_api_key()
            self.assertFalse(is_valid)
            self.assertFalse(is_valid)
    
    def test_http_error_handling(self):
        """HTTPエラーのハンドリングテスト"""
        with patch('requests.Session.get') as mock_get:
            # 404エラーを発生させる
            mock_get.return_value.status_code = 404
            mock_get.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
            
            # APIErrorが発生することを確認
            with self.assertRaises(APIError) as context:
                self.api.search("テストクエリ")
            
            self.assertIn("404", str(context.exception))
    
    def test_rate_limit_error(self):
        """レート制限エラーのテスト"""
        with patch('requests.Session.get') as mock_get:
            # 429エラーを発生させる
            mock_get.return_value.status_code = 429
            mock_get.return_value.json.return_value = {
                "error": {"message": "Rate limit exceeded"}
            }
            mock_get.return_value.content = b'{"error": {"message": "Rate limit exceeded"}}'
            
            # RateLimitErrorが発生することを確認
            with self.assertRaises(RateLimitError) as context:
                self.api.search("テストクエリ")
            
            self.assertIn("レート制限エラー", str(context.exception))
    
    def test_connection_error_handling(self):
        """接続エラーのハンドリングテスト"""
        with patch('requests.Session.get') as mock_get:
            # 接続エラーを発生させる
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
            
            # APIErrorが発生することを確認
            with self.assertRaises(APIError) as context:
                self.api.search("テストクエリ")
            
            self.assertIn("Connection failed", str(context.exception))
    
    def test_timeout_handling(self):
        """タイムアウトのハンドリングテスト"""
        with patch('requests.Session.get') as mock_get:
            # タイムアウトを発生させる
            mock_get.side_effect = requests.exceptions.Timeout("Request timeout")
            
            # APIErrorが発生することを確認
            with self.assertRaises(APIError) as context:
                self.api.search("テストクエリ")
            
            self.assertIn("Request timeout", str(context.exception))
    
    def test_retry_logic(self):
        """リトライ処理のテスト"""
        retry_api = GoogleSearchAPI(
            api_key=self.api_key,
            search_engine_id=self.search_engine_id,
            retry_count=3,
            retry_delay=0.01
        )
        
        # 成功レスポンス
        mock_success_response = {"items": []}
        
        with patch('requests.Session.get') as mock_get:
            # 最初の2回は失敗、3回目で成功
            mock_get.side_effect = [
                requests.exceptions.ConnectionError("Connection failed"),
                requests.exceptions.ConnectionError("Connection failed"),
                Mock(status_code=200, json=lambda: mock_success_response)
            ]
            mock_get.return_value.raise_for_status.return_value = None
            
            # 開始時間を記録
            start_time = time.time()
            
            # 検索を実行（リトライが発生するはず）
            result = retry_api.search("テストクエリ")
            
            # 実行時間を確認（リトライ待機時間が含まれているはず）
            execution_time = time.time() - start_time
            self.assertGreater(execution_time, 0.015)  # 少なくとも2回のretry_delay
            
            # 3回呼び出されたことを確認
            self.assertEqual(mock_get.call_count, 3)
            
            # 最終的に成功することを確認
            self.assertEqual(result, mock_success_response)
    
    def test_retry_exhaustion(self):
        """リトライ回数上限のテスト"""
        retry_api = GoogleSearchAPI(
            api_key=self.api_key,
            search_engine_id=self.search_engine_id,
            retry_count=2,
            retry_delay=0.01
        )
        
        with patch('requests.Session.get') as mock_get:
            # 全てのリトライで失敗
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
            
            # APIErrorが発生することを確認
            with self.assertRaises(APIError):
                retry_api.search("テストクエリ")
            
            # 指定回数+1回（初回+リトライ2回）呼び出されたことを確認
            self.assertEqual(mock_get.call_count, 3)
    
    def test_malformed_json_response(self):
        """不正なJSONレスポンスのテスト"""
        with patch('requests.Session.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_get.return_value.raise_for_status.return_value = None
            
            # APIErrorが発生することを確認
            with self.assertRaises(APIError) as context:
                self.api.search("テストクエリ")
            
            self.assertIn("JSON", str(context.exception))
    
    def test_empty_response(self):
        """空のレスポンスのテスト"""
        with patch('requests.Session.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {}
            mock_get.return_value.raise_for_status.return_value = None
            
            # 空のレスポンスでも正常に処理されることを確認
            result = self.api.search("テストクエリ")
            self.assertEqual(result, {})
    
    def test_large_response(self):
        """大きなレスポンスのテスト"""
        # 10個の検索結果を含むレスポンス
        mock_response = {
            "items": [
                {
                    "title": f"テストタイトル{i}",
                    "link": f"https://example{i}.com",
                    "snippet": f"テストスニペット{i}"
                }
                for i in range(10)
            ]
        }
        
        with patch('requests.Session.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status.return_value = None
            
            # 大きなレスポンスも正常に処理されることを確認
            result = self.api.search("テストクエリ", num=10)
            self.assertEqual(len(result["items"]), 10)
            self.assertEqual(result["items"][0]["title"], "テストタイトル0")
            self.assertEqual(result["items"][9]["title"], "テストタイトル9")


if __name__ == '__main__':
    unittest.main()

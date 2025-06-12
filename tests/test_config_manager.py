#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
設定管理テスト
ConfigManagerクラスの設定読み込み、環境変数、不正値処理のテスト
"""

import unittest
import tempfile
import os
import json
from unittest.mock import patch, mock_open
import sys
from pathlib import Path

# プロジェクトのsrcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    """ConfigManagerのテストクラス"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.json')
        
    def tearDown(self):
        """テスト後のクリーンアップ"""
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        os.rmdir(self.temp_dir)
    
    def test_valid_config_loading(self):
        """正常な設定ファイルの読み込みテスト"""
        # テスト用設定ファイルを作成
        test_config = {
            "google_api": {
                "api_key": "test_api_key",
                "custom_search_engine_id": "test_engine_id"
            },
            "output": {
                "directory": "test_output",
                "filename_prefix": "test_results"
            },
            "logging": {
                "level": "DEBUG",
                "file_path": "test_logs/test.log",
                "console_output": True
            },
            "search": {
                "retry_count": 5,
                "retry_delay": 2.0,
                "timeout": 15
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f, ensure_ascii=False, indent=2)
        
        # ConfigManagerで読み込み
        config = ConfigManager(config_file_path=self.config_file, skip_validation=True)
        
        # 読み込み結果を確認
        self.assertEqual(config.get_google_api_key(), "test_api_key")
        self.assertEqual(config.get_search_engine_id(), "test_engine_id")
        self.assertEqual(config.get_output_directory(), "test_output")
        self.assertEqual(config.get_output_filename_prefix(), "test_results")
        self.assertEqual(config.get_log_level(), "DEBUG")
        self.assertEqual(config.get_retry_count(), 5)
        self.assertEqual(config.get_retry_delay(), 2.0)
        self.assertEqual(config.get_timeout(), 15)
    
    @patch.dict(os.environ, {
        'GOOGLE_API_KEY': 'env_api_key',
        'GOOGLE_CUSTOM_SEARCH_ENGINE_ID': 'env_engine_id',
        'OUTPUT_DIRECTORY': 'env_output',
        'LOG_LEVEL': 'ERROR'
    })
    def test_environment_variables_override(self):
        """環境変数による設定上書きテスト"""
        # 基本設定ファイルを作成
        test_config = {
            "google_api": {
                "api_key": "file_api_key",
                "custom_search_engine_id": "file_engine_id"
            },
            "output": {
                "directory": "file_output"
            },
            "logging": {
                "level": "INFO"
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f, ensure_ascii=False, indent=2)
        
        # ConfigManagerで読み込み（環境変数が優先されるはず）
        config = ConfigManager(config_file_path=self.config_file, skip_validation=False)
        
        # 環境変数の値が使用されていることを確認
        self.assertEqual(config.get_google_api_key(), "env_api_key")
        self.assertEqual(config.get_search_engine_id(), "env_engine_id")
        self.assertEqual(config.get_output_directory(), "env_output")
        self.assertEqual(config.get_log_level(), "ERROR")
    
    def test_missing_required_config(self):
        """必須設定項目が不足している場合のテスト"""
        # 不完全な設定ファイルを作成
        test_config = {
            "output": {
                "directory": "test_output"
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f, ensure_ascii=False, indent=2)
        
        # 必須項目不足でValueErrorが発生することを確認
        # 環境変数をクリアしてテスト
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as context:
                ConfigManager(config_file_path=self.config_file, skip_validation=False)
        
        # エラーメッセージに不足項目が含まれていることを確認
        error_message = str(context.exception)
        self.assertIn("google_api.api_key", error_message)
        self.assertIn("google_api.custom_search_engine_id", error_message)
    
    def test_invalid_json_file(self):
        """不正なJSONファイルの処理テスト"""
        # 不正なJSONファイルを作成
        with open(self.config_file, 'w', encoding='utf-8') as f:
            f.write("{ invalid json content")
        
        # 環境変数で必須項目を設定
        with patch.dict(os.environ, {
            'GOOGLE_API_KEY': 'test_key',
            'GOOGLE_CUSTOM_SEARCH_ENGINE_ID': 'test_id'
        }):
            # 不正なJSONでも環境変数があれば正常に動作するはず
            config = ConfigManager(config_file_path=self.config_file)
            self.assertEqual(config.get_google_api_key(), "test_key")
    
    def test_nonexistent_config_file(self):
        """存在しない設定ファイルの処理テスト"""
        nonexistent_file = os.path.join(self.temp_dir, 'nonexistent.json')
        
        # 環境変数で必須項目を設定
        with patch.dict(os.environ, {
            'GOOGLE_API_KEY': 'test_key',
            'GOOGLE_CUSTOM_SEARCH_ENGINE_ID': 'test_id'
        }):
            # 存在しないファイルでも環境変数があれば正常に動作するはず
            config = ConfigManager(config_file_path=nonexistent_file)
            self.assertEqual(config.get_google_api_key(), "test_key")
    
    def test_default_values(self):
        """デフォルト値のテスト"""
        # 最小限の設定で ConfigManager を作成
        with patch.dict(os.environ, {
            'GOOGLE_API_KEY': 'test_key',
            'GOOGLE_CUSTOM_SEARCH_ENGINE_ID': 'test_id'
        }):
            config = ConfigManager(config_file_path=self.config_file)
            
            # デフォルト値が正しく設定されていることを確認
            self.assertEqual(config.get_output_directory(), "output")
            self.assertEqual(config.get_output_filename_prefix(), "search_results")
            self.assertEqual(config.get_log_level(), "INFO")
            self.assertEqual(config.get_retry_count(), 3)
            self.assertEqual(config.get_retry_delay(), 1.0)
            self.assertEqual(config.get_timeout(), 10)
    
    def test_invalid_values(self):
        """不正な設定値のテスト"""
        test_config = {
            "google_api": {
                "api_key": "test_key",
                "custom_search_engine_id": "test_id"
            },
            "search": {
                "retry_count": 15,  # 上限を超える値（0-10の範囲外）
                "retry_delay": -5.0,  # 不正値
                "timeout": 70  # 上限を超える値（1-60の範囲外）
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f, ensure_ascii=False, indent=2)
        
        # 不正値により例外が発生することを確認
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                ConfigManager(config_file_path=self.config_file, skip_validation=False)
    
    def test_valid_boundary_values(self):
        """境界値の正常ケーステスト"""
        test_config = {
            "google_api": {
                "api_key": "test_key",
                "custom_search_engine_id": "test_id"
            },
            "search": {
                "retry_count": 10,  # 上限値
                "retry_delay": 0.1,  # 最小値
                "timeout": 60  # 上限値
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f, ensure_ascii=False, indent=2)
        
        # 境界値でも正常に動作することを確認
        config = ConfigManager(config_file_path=self.config_file, skip_validation=True)
        self.assertEqual(config.get_retry_count(), 10)
        self.assertEqual(config.get_retry_delay(), 0.1)
        self.assertEqual(config.get_timeout(), 60)


if __name__ == '__main__':
    unittest.main()

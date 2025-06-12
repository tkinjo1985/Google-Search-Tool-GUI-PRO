#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Custom Search API接続モジュール
API認証処理、HTTPリクエスト処理、接続テスト機能を提供
"""

import requests
import time
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode


class APIError(Exception):
    """API関連の一般的なエラー"""
    pass


class RateLimitError(APIError):
    """レート制限エラー"""
    pass


class GoogleSearchAPI:
    """Google Custom Search API接続クラス"""
    
    def __init__(self, api_key: str, search_engine_id: str, 
                 timeout: int = 10, retry_count: int = 3, retry_delay: float = 1.0):
        """
        Google Custom Search API接続クラスの初期化
        
        Args:
            api_key: Google API キー
            search_engine_id: Custom Search Engine ID
            timeout: リクエストタイムアウト時間（秒）
            retry_count: リトライ回数
            retry_delay: リトライ間隔（秒）
        """
        self.api_key = api_key
        self.search_engine_id = search_engine_id
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        
        # API エンドポイント
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
        # ロガーを取得
        self.logger = logging.getLogger('google_search_tool.api')
          # セッションを作成（接続の再利用）
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Google-Search-Tool/1.0'
        })
    
    def _build_search_url(self, query: str, **kwargs) -> str:
        """
        検索APIのURLを構築
        
        Args:
            query: 検索クエリ
            **kwargs: 追加パラメータ
            
        Returns:
            APIリクエストURL
        """
        params = {
            'key': self.api_key,
            'cx': self.search_engine_id,
            'q': query,
            'num': kwargs.get('num', 1),  # GUI設定から取得可能
            'start': kwargs.get('start', 1),  # 開始位置
            'lr': kwargs.get('lr', 'lang_ja'),  # 言語制限
            'safe': kwargs.get('safe', 'off'),  # セーフサーチ
            'fileType': kwargs.get('fileType', ''),  # ファイルタイプ
            'siteSearch': kwargs.get('siteSearch', ''),  # サイト制限
            'gl': kwargs.get('gl', 'jp'),  # 地域制限
            'hl': kwargs.get('hl', 'ja'),  # 言語
        }
        
        # 空の値を削除
        params = {k: v for k, v in params.items() if v}
        
        return f"{self.base_url}?{urlencode(params)}"
    
    def _make_request(self, url: str) -> Dict[str, Any]:
        """
        APIリクエストを実行（リトライ機能付き）
        
        Args:
            url: リクエストURL
            
        Returns:
            APIレスポンス
            
        Raises:
            Exception: APIリクエストが失敗した場合
        """
        last_exception = None
        
        for attempt in range(self.retry_count + 1):
            try:
                self.logger.debug(f"APIリクエスト実行 (試行 {attempt + 1}/{self.retry_count + 1}): {url}")
                
                response = self.session.get(url, timeout=self.timeout)
                
                # HTTPステータスコードをチェック
                if response.status_code == 200:
                    try:
                        return response.json()
                    except ValueError as e:  # JSONDecodeError
                        raise APIError(f"不正なJSONレスポンス: {e}")
                elif response.status_code == 403:
                    try:
                        error_data = response.json() if response.content else {}
                    except ValueError:
                        error_data = {}
                    error_reason = error_data.get('error', {}).get('message', 'Unknown error')
                    if 'quota' in error_reason.lower() or 'limit' in error_reason.lower():
                        raise RateLimitError(f"API使用量制限に達しました: {error_reason}")
                    else:
                        raise APIError(f"API認証エラー: {error_reason}")
                elif response.status_code == 429:
                    try:
                        error_data = response.json() if response.content else {}
                    except ValueError:
                        error_data = {}
                    error_reason = error_data.get('error', {}).get('message', 'Rate limit exceeded')
                    raise RateLimitError(f"レート制限エラー: {error_reason}")
                elif response.status_code == 400:
                    try:
                        error_data = response.json() if response.content else {}
                    except ValueError:
                        error_data = {}
                    error_reason = error_data.get('error', {}).get('message', 'Bad Request')
                    raise APIError(f"APIリクエストエラー: {error_reason}")
                else:
                    raise APIError(f"APIリクエストが失敗しました (HTTP {response.status_code}): {response.text}")
                    
            except requests.exceptions.Timeout as e:
                last_exception = APIError(f"APIリクエストがタイムアウトしました: {e}")
                self.logger.warning(f"リクエストタイムアウト (試行 {attempt + 1}): {e}")
                
            except requests.exceptions.ConnectionError as e:
                last_exception = APIError(f"API接続エラー: {e}")
                self.logger.warning(f"接続エラー (試行 {attempt + 1}): {e}")
                
            except requests.exceptions.RequestException as e:
                last_exception = APIError(f"APIリクエストエラー: {e}")
                self.logger.warning(f"リクエストエラー (試行 {attempt + 1}): {e}")
                
            except ValueError as e:
                # JSON decode error
                last_exception = APIError(f"不正なJSONレスポンス: {e}")
                self.logger.warning(f"JSONデコードエラー (試行 {attempt + 1}): {e}")
                
            except Exception as e:
                # APIエラーレスポンスやその他の例外
                if 'quota' in str(e).lower() or 'limit' in str(e).lower():
                    # 使用量制限の場合はリトライしない
                    raise e
                last_exception = e
                self.logger.warning(f"予期しないエラー (試行 {attempt + 1}): {e}")
            
            # 最後の試行でない場合は待機
            if attempt < self.retry_count:
                self.logger.info(f"リトライまで {self.retry_delay} 秒待機中...")
                time.sleep(self.retry_delay)
        
        # すべてのリトライが失敗した場合
        raise last_exception or APIError("APIリクエストが失敗しました")
    
    def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        検索を実行
        
        Args:
            query: 検索クエリ
            **kwargs: 追加の検索パラメータ
            
        Returns:
            検索結果
        """
        if not query or not query.strip():
            raise ValueError("検索クエリが空です")
        
        self.logger.info(f"検索実行: '{query}'")
        
        try:
            url = self._build_search_url(query.strip(), **kwargs)
            result = self._make_request(url)
            
            # 検索結果の基本情報をログ出力
            total_results = result.get('searchInformation', {}).get('totalResults', '0')
            search_time = result.get('searchInformation', {}).get('searchTime', '0')
            items_count = len(result.get('items', []))
            
            self.logger.info(f"検索完了: 総結果数={total_results}, 取得件数={items_count}, 処理時間={search_time}秒")
            
            return result
            
        except Exception as e:
            self.logger.error(f"検索エラー: {e}")
            raise
    
    def get_first_result(self, query: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        検索結果の1位を取得
        
        Args:
            query: 検索クエリ
            **kwargs: 追加の検索パラメータ
            
        Returns:
            1位の検索結果（結果がない場合はNone）
        """
        try:
            result = self.search(query, num=1, **kwargs)
            items = result.get('items', [])
            
            if items:
                first_item = items[0]
                self.logger.debug(f"1位結果: {first_item.get('title', '')} - {first_item.get('link', '')}")
                return first_item
            else:
                self.logger.warning(f"検索結果が見つかりませんでした: '{query}'")
                return None
                
        except Exception as e:
            self.logger.error(f"1位結果取得エラー: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        API接続をテスト
        
        Returns:
            接続成功の場合True、失敗の場合False
        """
        try:
            self.logger.info("API接続テストを実行中...")
            
            # 簡単なテスト検索を実行
            test_query = "test"
            result = self.search(test_query, num=1)
            
            # レスポンスの基本構造をチェック
            if 'searchInformation' in result:
                self.logger.info("API接続テスト成功")
                return True
            else:
                self.logger.error("API接続テスト失敗: 不正なレスポンス形式")
                return False
                
        except Exception as e:
            self.logger.error(f"API接続テスト失敗: {e}")
            return False
    
    def validate_api_key(self) -> bool:
        """
        APIキーの有効性を検証
        
        Returns:
            APIキーが有効な場合True、無効な場合False
        """
        if not self.api_key or self.api_key == "YOUR_GOOGLE_API_KEY_HERE":
            self.logger.error("APIキーが設定されていません")
            return False
        
        if not self.search_engine_id or self.search_engine_id == "YOUR_CUSTOM_SEARCH_ENGINE_ID_HERE":
            self.logger.error("Custom Search Engine IDが設定されていません")
            return False
        
        return self.test_connection()
    
    def get_usage_info(self) -> Dict[str, Any]:
        """
        API使用量情報を取得（概算）
        
        Returns:
            使用量情報
        """
        # 注意: Google Custom Search APIは直接的な使用量取得APIを提供していないため、
        # ここでは基本的な情報のみを返す
        return {
            "api_key_length": len(self.api_key) if self.api_key else 0,
            "search_engine_id_length": len(self.search_engine_id) if self.search_engine_id else 0,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "retry_delay": self.retry_delay
        }
    
    def close(self) -> None:
        """リソースをクリーンアップ"""
        if hasattr(self, 'session'):
            self.session.close()
            self.logger.debug("APIセッションを閉じました")


if __name__ == "__main__":
    # テスト実行
    import sys
    import os
    
    # 設定ファイルからAPIキーを読み込み
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        from config_manager import ConfigManager
        from logger_config import setup_logger_from_config
        
        # 設定を読み込み
        config = ConfigManager()
        logger = setup_logger_from_config(config)
        
        # API接続テスト
        api = GoogleSearchAPI(
            api_key=config.get_google_api_key(),
            search_engine_id=config.get_search_engine_id(),
            timeout=config.get_timeout(),
            retry_count=config.get_retry_count(),
            retry_delay=config.get_retry_delay()
        )
        
        print("API接続テストを実行中...")
        if api.validate_api_key():
            print("✅ API接続テスト成功")
            
            # テスト検索
            test_query = "Python プログラミング"
            print(f"\nテスト検索: '{test_query}'")
            first_result = api.get_first_result(test_query)
            
            if first_result:
                print(f"✅ 検索成功")
                print(f"タイトル: {first_result.get('title', '')}")
                print(f"URL: {first_result.get('link', '')}")
                print(f"スニペット: {first_result.get('snippet', '')[:100]}...")
            else:
                print("❌ 検索結果が見つかりませんでした")
        else:
            print("❌ API接続テスト失敗")
            
        api.close()
        
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        print("注意: API キーと Search Engine ID が正しく設定されていることを確認してください")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
検索エンジンモジュール
Google Custom Search APIを使用した検索機能とエラーハンドリングを提供
"""

import logging
import time
from typing import List, Optional, Dict, Any
from google_search_api import GoogleSearchAPI
from search_result import SearchResult, SearchResultFilter


class SearchEngine:
    """検索エンジンクラス"""
    
    def __init__(self, api_key: str, search_engine_id: str,
                 timeout: int = 10, retry_count: int = 3, retry_delay: float = 1.0):
        """
        検索エンジンの初期化
        
        Args:
            api_key: Google API キー
            search_engine_id: Custom Search Engine ID
            timeout: リクエストタイムアウト時間（秒）
            retry_count: リトライ回数
            retry_delay: リトライ間隔（秒）
        """
        self.api = GoogleSearchAPI(
            api_key=api_key,
            search_engine_id=search_engine_id,
            timeout=timeout,
            retry_count=retry_count,
            retry_delay=retry_delay
        )
        
        self.filter = SearchResultFilter()
        self.logger = logging.getLogger('google_search_tool.search_engine')
          # 検索統計情報
        self.stats = {
            'total_searches': 0,
            'successful_searches': 0,
            'failed_searches': 0,
            'total_results_found': 0
        }
    
    def search_single_keyword(self, query: str, get_first_only: bool = True, num_results: int = 1) -> Optional[SearchResult]:
        """
        単一キーワードで検索し、1位の結果を取得
        
        Args:
            query: 検索クエリ
            get_first_only: 1位のみ取得するかどうか
            num_results: 取得する検索結果数（デフォルト: 1）
            
        Returns:
            検索結果（1位）、見つからない場合はNone
        """
        if not query or not query.strip():
            self.logger.error("検索クエリが空です")
            return None
        
        query = query.strip()
        self.logger.info(f"検索開始: '{query}'")
        
        try:
            self.stats['total_searches'] += 1
            
            # numパラメータを使用してAPI検索を実行
            search_num = 1 if get_first_only else min(num_results, 10)  # APIの制限により最大10件
            api_result = self.api.search(query, num=search_num)
            
            # 検索結果を解析
            items = api_result.get('items', [])
            if not items:
                self.logger.warning(f"検索結果が見つかりませんでした: '{query}'")
                self.stats['failed_searches'] += 1
                return None
            
            # 最初の結果をSearchResultオブジェクトに変換
            first_item = items[0]
            result = SearchResult.from_google_api_response(first_item, query, 1)
            
            # フィルタリング
            if not self.filter.is_valid_result(result):
                self.logger.warning(f"検索結果がフィルタリングされました: '{query}'")
                self.stats['failed_searches'] += 1
                return None
            
            self.stats['successful_searches'] += 1
            self.stats['total_results_found'] += 1
            
            self.logger.info(f"検索成功: '{query}' -> '{result.title}'")
            return result
            
        except Exception as e:
            self.logger.error(f"検索エラー: '{query}' - {e}")
            self.stats['failed_searches'] += 1
            raise SearchEngineError(f"検索に失敗しました: {e}")
    
    def search_multiple_keywords(self, queries: List[str], 
                                delay_between_searches: float = 1.0) -> List[SearchResult]:
        """
        複数キーワードで順次検索を実行
        
        Args:
            queries: 検索クエリのリスト
            delay_between_searches: 検索間隔（秒）
            
        Returns:
            検索結果のリスト
        """
        if not queries:
            self.logger.error("検索クエリリストが空です")
            return []
        
        results = []
        total_queries = len(queries)
        
        self.logger.info(f"複数キーワード検索開始: {total_queries}件")
        
        for i, query in enumerate(queries, 1):
            try:
                self.logger.info(f"進捗: {i}/{total_queries} - '{query}'")
                
                result = self.search_single_keyword(query)
                if result:
                    results.append(result)
                    self.logger.debug(f"検索成功: {len(results)}件目")
                else:
                    self.logger.warning(f"検索結果なし: '{query}'")
                
                # 最後の検索でない場合は待機
                if i < total_queries and delay_between_searches > 0:
                    self.logger.debug(f"次の検索まで {delay_between_searches} 秒待機中...")
                    time.sleep(delay_between_searches)
                    
            except Exception as e:
                self.logger.error(f"検索エラー: '{query}' - {e}")
                # エラーが発生しても続行
                continue
        
        self.logger.info(f"複数キーワード検索完了: {len(results)}/{total_queries}件成功")
        return results
    
    def search_with_retry(self, query: str, max_retries: int = None) -> Optional[SearchResult]:
        """
        リトライ機能付きの検索
        
        Args:
            query: 検索クエリ
            max_retries: 最大リトライ回数（省略時は設定値を使用）
            
        Returns:
            検索結果
        """
        if max_retries is None:
            max_retries = self.api.retry_count
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    self.logger.info(f"リトライ {attempt}/{max_retries}: '{query}'")
                
                return self.search_single_keyword(query)
                
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = self.api.retry_delay * (attempt + 1)  # 指数バックオフ
                    self.logger.warning(f"検索失敗、{wait_time}秒後にリトライ: {e}")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"最大リトライ回数に達しました: '{query}'")
        
        if last_exception:
            raise last_exception
        
        return None
    
    def validate_connection(self) -> bool:
        """API接続の有効性を検証"""
        try:
            return self.api.validate_api_key()
        except Exception as e:
            self.logger.error(f"API接続検証エラー: {e}")
            return False
    
    def get_search_stats(self) -> Dict[str, Any]:
        """検索統計情報を取得"""
        success_rate = 0
        if self.stats['total_searches'] > 0:
            success_rate = (self.stats['successful_searches'] / self.stats['total_searches']) * 100
        
        return {
            **self.stats,
            'success_rate': round(success_rate, 2),
            'api_info': self.api.get_usage_info()
        }
    
    def reset_stats(self) -> None:
        """統計情報をリセット"""
        self.stats = {
            'total_searches': 0,
            'successful_searches': 0,
            'failed_searches': 0,
            'total_results_found': 0
        }
        self.logger.info("検索統計情報をリセットしました")
    
    def search_multiple_results(self, query: str, num_results: int = 1) -> List[SearchResult]:
        """
        複数の検索結果を取得
        
        Args:
            query: 検索クエリ
            num_results: 取得する検索結果数（最大10）
            
        Returns:
            検索結果のリスト
        """
        if not query or not query.strip():
            self.logger.error("検索クエリが空です")
            return []
        
        query = query.strip()
        self.logger.info(f"複数結果検索開始: '{query}' (件数: {num_results})")
        
        try:
            self.stats['total_searches'] += 1
            
            # Google APIから複数結果を取得
            search_num = min(num_results, 10)  # APIの制限により最大10件
            api_result = self.api.search(query, num=search_num)
            
            # 検索結果を解析
            items = api_result.get('items', [])
            if not items:
                self.logger.warning(f"検索結果が見つかりませんでした: '{query}'")
                self.stats['failed_searches'] += 1
                return []
            
            results = []
            for idx, item in enumerate(items[:num_results]):
                try:
                    # 各結果をSearchResultオブジェクトに変換
                    result = SearchResult.from_google_api_response(item, query, idx + 1)
                    
                    # フィルタリング
                    if self.filter.is_valid_result(result):
                        results.append(result)
                        self.stats['total_results_found'] += 1
                    else:
                        self.logger.debug(f"結果がフィルタリングされました: {result.title}")
                        
                except Exception as e:
                    self.logger.warning(f"結果の処理でエラー: {e}")
                    continue
            
            if results:
                self.stats['successful_searches'] += 1
                self.logger.info(f"複数結果検索成功: '{query}' -> {len(results)}件取得")
            else:
                self.stats['failed_searches'] += 1
                self.logger.warning(f"有効な検索結果がありませんでした: '{query}'")
            
            return results
            
        except Exception as e:
            self.logger.error(f"複数結果検索エラー: '{query}' - {e}")
            self.stats['failed_searches'] += 1
            raise SearchEngineError(f"検索に失敗しました: {e}")
    
    def search_single_keyword_with_params(self, query: str, search_params: dict = None) -> Optional[SearchResult]:
        """
        単一キーワードで検索し、検索パラメータを適用
        
        Args:
            query: 検索クエリ
            search_params: 検索パラメータ（lr、safe、gl、hl）
            
        Returns:
            検索結果（1位）、見つからない場合はNone
        """
        if not query or not query.strip():
            self.logger.error("検索クエリが空です")
            return None
        
        query = query.strip()
        self.logger.info(f"検索開始（パラメータ付き）: '{query}' - {search_params}")
        
        try:
            self.stats['total_searches'] += 1
            
            # numパラメータを使用してAPI検索を実行（検索パラメータ付き）
            api_result = self.api.search(query, num=1, **search_params)
            
            # 検索結果を解析
            items = api_result.get('items', [])
            if not items:
                self.logger.warning(f"検索結果が見つかりませんでした: '{query}'")
                self.stats['failed_searches'] += 1
                return None
            
            # 最初の結果をSearchResultオブジェクトに変換
            first_item = items[0]
            result = SearchResult.from_google_api_response(first_item, query, 1)
            
            # フィルタリング
            if not self.filter.is_valid_result(result):
                self.logger.warning(f"検索結果がフィルタリングされました: '{query}'")
                self.stats['failed_searches'] += 1
                return None
            
            self.stats['successful_searches'] += 1
            self.stats['total_results_found'] += 1
            
            self.logger.info(f"検索成功: '{query}' -> '{result.title}'")
            return result
            
        except Exception as e:
            self.logger.error(f"検索エラー: '{query}' - {e}")
            self.stats['failed_searches'] += 1
            raise SearchEngineError(f"検索に失敗しました: {e}")
    
    def search_multiple_results_with_params(self, query: str, num_results: int = 1, search_params: dict = None) -> List[SearchResult]:
        """
        複数の検索結果を取得（検索パラメータ付き）
        
        Args:
            query: 検索クエリ
            num_results: 取得する検索結果数（最大10）
            search_params: 検索パラメータ（lr、safe、gl、hl）
            
        Returns:
            検索結果のリスト
        """
        if not query or not query.strip():
            self.logger.error("検索クエリが空です")
            return []
        
        query = query.strip()
        self.logger.info(f"複数結果検索開始（パラメータ付き）: '{query}' (件数: {num_results}) - {search_params}")
        
        try:
            self.stats['total_searches'] += 1
            
            # Google APIから複数結果を取得（検索パラメータ付き）
            search_num = min(num_results, 10)  # APIの制限により最大10件
            api_result = self.api.search(query, num=search_num, **search_params)
            
            # 検索結果を解析
            items = api_result.get('items', [])
            if not items:
                self.logger.warning(f"検索結果が見つかりませんでした: '{query}'")
                self.stats['failed_searches'] += 1
                return []
            
            results = []
            for idx, item in enumerate(items[:num_results]):
                try:
                    # 各結果をSearchResultオブジェクトに変換
                    result = SearchResult.from_google_api_response(item, query, idx + 1)
                    
                    # フィルタリング
                    if self.filter.is_valid_result(result):
                        results.append(result)
                        self.stats['total_results_found'] += 1
                    else:
                        self.logger.debug(f"結果がフィルタリングされました: {result.title}")
                        
                except Exception as e:
                    self.logger.warning(f"結果の処理でエラー: {e}")
                    continue
            
            if results:
                self.stats['successful_searches'] += 1
                self.logger.info(f"複数結果検索成功: '{query}' -> {len(results)}件取得")
            else:
                self.stats['failed_searches'] += 1
                self.logger.warning(f"有効な検索結果がありませんでした: '{query}'")
            
            return results
            
        except Exception as e:
            self.logger.error(f"複数結果検索エラー: '{query}' - {e}")
            self.stats['failed_searches'] += 1
            raise SearchEngineError(f"検索に失敗しました: {e}")

    def close(self) -> None:
        """リソースをクリーンアップ"""
        if hasattr(self.api, 'close'):
            self.api.close()
        self.logger.info("検索エンジンを終了しました")
    

class SearchEngineError(Exception):
    """検索エンジン関連のエラー"""
    pass


class QuotaExceededError(SearchEngineError):
    """API使用量制限エラー"""
    pass


class RateLimitError(SearchEngineError):
    """レート制限エラー"""
    pass


def create_search_engine_from_config(config_manager) -> SearchEngine:
    """
    設定管理クラスから検索エンジンを作成
    
    Args:
        config_manager: ConfigManagerのインスタンス
        
    Returns:
        設定された検索エンジン
    """
    return SearchEngine(
        api_key=config_manager.get_google_api_key(),
        search_engine_id=config_manager.get_search_engine_id(),
        timeout=config_manager.get_timeout(),
        retry_count=config_manager.get_retry_count(),
        retry_delay=config_manager.get_retry_delay()
    )


if __name__ == "__main__":
    # テスト実行
    import sys
    import os
    
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        from config_manager import ConfigManager
        from logger_config import setup_logger_from_config
        
        # 設定を読み込み
        config = ConfigManager()
        logger = setup_logger_from_config(config)
        
        # 検索エンジンを作成
        search_engine = create_search_engine_from_config(config)
        
        print("検索エンジンのテストを実行中...")
        
        # 接続テスト
        if search_engine.validate_connection():
            print("✅ API接続テスト成功")
            
            # 単一キーワード検索テスト
            test_queries = ["Python プログラミング", "機械学習 入門"]
            
            print(f"\n単一キーワード検索テスト:")
            for query in test_queries:
                try:
                    result = search_engine.search_single_keyword(query)
                    if result:
                        print(f"✅ '{query}' -> {result.title[:50]}...")
                    else:
                        print(f"❌ '{query}' -> 結果なし")
                except Exception as e:
                    print(f"❌ '{query}' -> エラー: {e}")
            
            # 統計情報を表示
            stats = search_engine.get_search_stats()
            print(f"\n検索統計:")
            print(f"総検索数: {stats['total_searches']}")
            print(f"成功数: {stats['successful_searches']}")
            print(f"成功率: {stats['success_rate']}%")
            
        else:
            print("❌ API接続テスト失敗")
        
        search_engine.close()
        
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        print("注意: API キーと Search Engine ID が正しく設定されていることを確認してください")

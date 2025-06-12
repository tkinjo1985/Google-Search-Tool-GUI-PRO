#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
検索エンジンの制御ロジック
GUI専用のSearchTool - GUIアプリケーションから利用される検索機能を提供
"""

import sys
import os
import time
import logging
import signal
from datetime import datetime
from typing import List, Optional

# プロジェクトのsrcディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_manager import ConfigManager
from logger_config import setup_logger_from_config
from search_engine import SearchEngine, create_search_engine_from_config
from csv_writer import CSVWriter, create_csv_writer_from_config
from search_result import SearchResult


class SearchTool:
    """GUI専用検索ツールクラス"""
    
    def __init__(self, setup_signals: bool = True):
        """検索ツールの初期化"""
        self.config = None
        self.logger = None
        self.search_engine = None
        self.csv_writer = None
        
        # 実行統計
        self.start_time = None
        self.end_time = None
        self.processed_keywords = []
        self.successful_results = []
        self.failed_keywords = []
        
        # 終了フラグ
        self.interrupted = False
        
        # シグナルハンドラーの設定（GUI環境では無効化可能）
        if setup_signals:
            self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """シグナルハンドラーを設定（グレースフル終了対応）"""
        try:
            def signal_handler(signum, frame):
                if self.logger:
                    self.logger.info(f"終了シグナルを受信しました (signal {signum})")
                self.interrupted = True
                
            signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
            signal.signal(signal.SIGTERM, signal_handler)  # Terminate
        except ValueError as e:
            # メインスレッドでない場合（GUI環境など）は無視
            if "signal only works in main thread" in str(e):
                pass  # GUI環境では正常な動作
            else:
                raise e
    
    def initialize_for_test(self, config_manager: 'ConfigManager') -> bool:
        """
        テスト用の初期化
        
        Args:
            config_manager: 設定管理オブジェクト
            
        Returns:
            初期化成功の場合True
        """
        try:
            # 設定を直接設定
            self.config = config_manager
            
            # ログ設定
            self.logger = setup_logger_from_config(self.config)
            self.logger.info("Google Search Tool をテストモードで起動しました")
              # 検索エンジンを初期化
            self.search_engine = create_search_engine_from_config(self.config)
            
            # CSV出力クラスを初期化
            self.csv_writer = create_csv_writer_from_config(self.config)
            
            self.logger.info("テスト用初期化完了")
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"テスト用初期化エラー: {e}")
            return False
    
    def test_connection(self) -> bool:
        """API接続をテスト"""
        if not self.search_engine:
            return False
            
        try:
            self.logger.info("API接続テストを実行中...")
            
            if self.search_engine.validate_connection():
                self.logger.info("✅ API接続テスト成功")
                return True
            else:
                self.logger.error("❌ API接続テスト失敗")
                return False
        except Exception as e:
            self.logger.error(f"API接続テストエラー: {e}")
            return False
    
    def run_search(self, keywords: List[str], search_delay: float = 1.0, num_results: int = 1) -> List[SearchResult]:
        """
        検索を実行
        
        Args:
            keywords: 検索キーワードのリスト
            search_delay: 検索間隔（秒）
            num_results: 取得する検索結果数（デフォルト: 1）
            
        Returns:
            検索結果のリスト
        """
        if not keywords:
            self.logger.error("検索キーワードがありません")
            return []
        
        self.start_time = datetime.now()
        results = []
        total_keywords = len(keywords)
        
        self.logger.info(f"バッチ検索開始: {total_keywords}件のキーワード")
        
        for i, keyword in enumerate(keywords, 1):
            if self.interrupted:
                self.logger.info("検索が中断されました")
                break
            
            try:
                # 検索実行
                self.logger.info(f"[{i:3d}/{total_keywords}] 検索中: '{keyword}'")
                
                result = self.search_engine.search_single_keyword(keyword, get_first_only=(num_results == 1), num_results=num_results)
                
                if result:
                    results.append(result)
                    self.successful_results.append(result)
                    self.logger.info(f"[{i:3d}/{total_keywords}] ✅ 成功: '{result.title[:50]}...'")
                else:
                    self.failed_keywords.append(keyword)
                    self.logger.warning(f"[{i:3d}/{total_keywords}] ❌ 結果なし")
                
                self.processed_keywords.append(keyword)
                
                # 最後のキーワードでない場合は待機
                if i < total_keywords and search_delay > 0:
                    self.logger.debug(f"次の検索まで {search_delay} 秒待機中...")
                    time.sleep(search_delay)
                
            except KeyboardInterrupt:
                self.logger.info("ユーザーにより検索が中断されました")
                self.interrupted = True
                break
                
            except Exception as e:
                self.failed_keywords.append(keyword)
                self.logger.error(f"[{i:3d}/{total_keywords}] ❌ エラー: {e}")
                # エラーが発生しても続行
                continue
        
        self.end_time = datetime.now()
        
        # 検索統計をログに記録
        self._log_search_summary(results, total_keywords)
        
        return results
    
    def _log_search_summary(self, results: List[SearchResult], total_keywords: int) -> None:
        """検索結果のサマリーをログに記録"""
        execution_time = (self.end_time - self.start_time).total_seconds()
        success_count = len(results)
        failure_count = len(self.failed_keywords)
        success_rate = (success_count / total_keywords * 100) if total_keywords > 0 else 0
        
        self.logger.info(f"検索完了 - 総キーワード数: {total_keywords}")
        self.logger.info(f"検索完了 - 成功数: {success_count}")
        self.logger.info(f"検索完了 - 失敗数: {failure_count}")
        self.logger.info(f"検索完了 - 成功率: {success_rate:.1f}%")
        self.logger.info(f"検索完了 - 実行時間: {execution_time:.1f} 秒")
        
        if self.interrupted:
            self.logger.info("※ 検索は途中で中断されました")
    
    def save_results(self, results: List[SearchResult], filename: str = None) -> Optional[str]:
        """
        検索結果をCSVファイルに保存
        
        Args:
            results: 検索結果のリスト
            filename: 出力ファイル名（省略時は自動生成）
              Returns:
            保存されたファイルのパス
        """
        if not results:
            self.logger.warning("保存する検索結果がありません")
            return None
        
        try:
            self.logger.info(f"CSV出力開始: {len(results)}件")
            
            output_file = self.csv_writer.write_results(results, filename)
            
            if output_file:
                self.logger.info(f"CSV出力完了: {output_file}")
                
                # サマリーファイルも作成
                try:
                    stats = self.search_engine.get_search_stats()
                    summary_file = self.csv_writer.create_summary_file(results, stats)
                    self.logger.info(f"サマリーファイル作成完了: {summary_file}")
                except Exception as e:
                    self.logger.warning(f"サマリーファイル作成エラー: {e}")
                
                return output_file
            else:
                self.logger.error("CSV出力に失敗しました")
                return None
        except Exception as e:
            self.logger.error(f"結果保存エラー: {e}")
            return None
    
    def search_keywords_batch(self, keywords: List[str], search_delay: float = 1.0, 
                             progress_callback=None, num_results: int = 1) -> List[SearchResult]:
        """
        バッチ検索の実行（GUI用進捗コールバック対応）
        
        Args:
            keywords: 検索キーワードのリスト
            search_delay: 検索間隔（秒）
            progress_callback: 進捗通知コールバック
            num_results: 取得する検索結果数（デフォルト: 1）
              Returns:
            検索結果のリスト
        """
        if not keywords:
            self.logger.error("検索キーワードがありません")
            return []
        
        self.start_time = datetime.now()
        results = []
        total_keywords = len(keywords)
        
        self.logger.info(f"バッチ検索開始: {total_keywords}件のキーワード")
        
        for i, keyword in enumerate(keywords):
            if self.interrupted:
                self.logger.info("検索が中断されました")
                break
            
            try:
                # 進捗通知
                if progress_callback:
                    progress = int((i / total_keywords) * 100)
                    progress_callback(progress, f"検索中 ({i+1}/{total_keywords}): {keyword}")
                
                # 検索実行
                result = self.search_single_keyword(keyword, num_results)
                
                if result:
                    results.append(result)
                
                # 最後のキーワードでない場合は待機
                if i < total_keywords - 1 and search_delay > 0:
                    time.sleep(search_delay)
                
            except Exception as e:
                self.logger.error(f"バッチ検索エラー: {keyword} - {e}")
                continue
        
        self.end_time = datetime.now()
        self.logger.info(f"バッチ検索完了: {len(results)}/{total_keywords}件成功")
        
        return results
    
    def search_single_keyword(self, keyword: str, num_results: int = 1) -> Optional[SearchResult]:
        """
        単一キーワードの検索
        
        Args:
            keyword: 検索キーワード
            num_results: 取得する検索結果数（デフォルト: 1）
            
        Returns:
            検索結果（成功時）またはNone（失敗時）
        """
        if not self.search_engine:
            self.logger.error("検索エンジンが初期化されていません")
            return None
            
        try:
            result = self.search_engine.search_single_keyword(keyword, get_first_only=(num_results == 1), num_results=num_results)
            
            if result:
                self.successful_results.append(result)
                self.logger.info(f"検索成功: '{keyword}' -> '{result.title[:50]}...'")
            else:
                self.failed_keywords.append(keyword)
                self.logger.warning(f"検索結果なし: '{keyword}'")
            
            self.processed_keywords.append(keyword)
            return result
            
        except Exception as e:
            self.failed_keywords.append(keyword)
            self.logger.error(f"検索エラー: '{keyword}' - {e}")
            return None
    
    def search_multiple_keywords(self, keyword: str, num_results: int = 1) -> List[SearchResult]:
        """
        単一キーワードで複数の検索結果を取得
        
        Args:
            keyword: 検索キーワード
            num_results: 取得する検索結果数（デフォルト: 1）
            
        Returns:
            検索結果のリスト
        """
        if not self.search_engine:
            self.logger.error("検索エンジンが初期化されていません")
            return []
            
        try:
            results = self.search_engine.search_multiple_results(keyword, num_results)
            
            for result in results:
                self.successful_results.append(result)
                self.logger.info(f"検索成功: '{keyword}' -> '{result.title[:50]}...'")
            
            if not results:
                self.failed_keywords.append(keyword)
                self.logger.warning(f"検索結果なし: '{keyword}'")
            
            self.processed_keywords.append(keyword)
            return results
            
        except Exception as e:
            self.failed_keywords.append(keyword)
            self.logger.error(f"検索エラー: '{keyword}' - {e}")
            return []
    
    def search_single_keyword_with_params(self, keyword: str, search_params: dict = None) -> Optional[SearchResult]:
        """
        単一キーワードの検索（検索パラメータ付き）
        
        Args:
            keyword: 検索キーワード
            search_params: 検索パラメータ（lr、safe、gl、hl）
            
        Returns:
            検索結果（成功時）またはNone（失敗時）
        """
        if not self.search_engine:
            self.logger.error("検索エンジンが初期化されていません")
            return None
            
        try:
            result = self.search_engine.search_single_keyword_with_params(keyword, search_params or {})
            
            if result:
                self.successful_results.append(result)
                self.logger.info(f"検索成功: '{keyword}' -> '{result.title[:50]}...'")
            else:
                self.failed_keywords.append(keyword)
                self.logger.warning(f"検索結果なし: '{keyword}'")
            
            self.processed_keywords.append(keyword)
            return result
            
        except Exception as e:
            self.failed_keywords.append(keyword)
            self.logger.error(f"検索エラー: '{keyword}' - {e}")
            return None
    
    def search_multiple_keywords_with_params(self, keyword: str, num_results: int = 1, search_params: dict = None) -> List[SearchResult]:
        """
        単一キーワードで複数の検索結果を取得（検索パラメータ付き）
        
        Args:
            keyword: 検索キーワード
            num_results: 取得する検索結果数（デフォルト: 1）
            search_params: 検索パラメータ（lr、safe、gl、hl）
            
        Returns:
            検索結果のリスト
        """
        if not self.search_engine:
            self.logger.error("検索エンジンが初期化されていません")
            return []
            
        try:
            results = self.search_engine.search_multiple_results_with_params(keyword, num_results, search_params or {})
            
            for result in results:
                self.successful_results.append(result)
                self.logger.info(f"検索成功: '{keyword}' -> '{result.title[:50]}...'")
            
            if not results:
                self.failed_keywords.append(keyword)
                self.logger.warning(f"検索結果なし: '{keyword}'")
            
            self.processed_keywords.append(keyword)
            return results
            
        except Exception as e:
            self.failed_keywords.append(keyword)
            self.logger.error(f"検索エラー: '{keyword}' - {e}")
            return []

    def stop_search(self):
        """検索を停止"""
        self.interrupted = True
        self.logger.info("検索停止が要求されました")
    
    def reset_stats(self):
        """統計をリセット"""
        self.processed_keywords.clear()
        self.successful_results.clear()
        self.failed_keywords.clear()
        self.interrupted = False
        self.start_time = None
        self.end_time = None
    
    def get_search_stats(self) -> dict:
        """
        検索統計を取得
        
        Returns:
            検索統計の辞書
        """
        total_processed = len(self.processed_keywords)
        successful_count = len(self.successful_results)
        failed_count = len(self.failed_keywords)
        success_rate = (successful_count / total_processed * 100) if total_processed > 0 else 0
        
        execution_time = 0
        if self.start_time and self.end_time:
            execution_time = (self.end_time - self.start_time).total_seconds()
        
        return {
            'total_processed': total_processed,
            'successful_count': successful_count,
            'failed_count': failed_count,
            'success_rate': success_rate,
            'execution_time': execution_time,
            'interrupted': self.interrupted
        }
    
    def cleanup(self):
        """リソースクリーンアップ"""
        try:
            if self.search_engine:
                self.search_engine.close()
            
            if self.logger:
                self.logger.info("Search Tool GUI を終了します")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"クリーンアップエラー: {e}")
    
    def initialize_for_gui(self) -> bool:
        """
        GUI用のツール初期化（設定検証をスキップ）
        
        Returns:
            初期化成功の場合True
        """
        try:
            # 設定読み込み（検証をスキップ）
            self.config = ConfigManager(skip_validation=True)
            
            # ログ設定
            self.logger = setup_logger_from_config(self.config)
            self.logger.info("Google Search Tool をGUIモードで起動しました")
            
            # 検索エンジンを初期化
            self.search_engine = create_search_engine_from_config(self.config)
            
            # CSV出力クラスを初期化
            self.csv_writer = create_csv_writer_from_config(self.config)
            
            self.logger.info("GUI用初期化完了")
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"GUI用初期化エラー: {e}")
            return False


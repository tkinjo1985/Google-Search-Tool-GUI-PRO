#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ログ設定モジュール
ファイル出力とコンソール出力の設定、ログレベル管理機能を提供
"""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional


class LoggerConfig:
    """ログ設定クラス"""
    
    def __init__(self, 
                 log_file_path: str = "logs/search.log",
                 log_level: str = "INFO",
                 console_output: bool = True,
                 max_file_size: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5):
        """
        ログ設定クラスの初期化
        
        Args:
            log_file_path: ログファイルのパス
            log_level: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
            console_output: コンソール出力の有無
            max_file_size: ログファイルの最大サイズ（バイト）
            backup_count: バックアップファイル数
        """
        self.log_file_path = log_file_path
        self.log_level = self._get_log_level(log_level)
        self.console_output = console_output
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        
        # ログディレクトリを作成
        log_dir = os.path.dirname(self.log_file_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        # ロガーを設定
        self.logger = self._setup_logger()
    
    def _get_log_level(self, level_str: str) -> int:
        """文字列からログレベルを取得"""
        level_mapping = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        return level_mapping.get(level_str.upper(), logging.INFO)
    
    def _setup_logger(self) -> logging.Logger:
        """ロガーをセットアップ"""
        logger = logging.getLogger('google_search_tool')
        logger.setLevel(self.log_level)
        
        # 既存のハンドラーをクリア
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # フォーマッターを作成
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # ファイルハンドラーを追加（ローテーション対応）
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                self.log_file_path,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(self.log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"警告: ログファイルハンドラーの作成に失敗しました: {e}")
        
        # コンソールハンドラーを追加
        if self.console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.log_level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        return logger
    
    def get_logger(self) -> logging.Logger:
        """ロガーを取得"""
        return self.logger
    
    def set_log_level(self, level_str: str) -> None:
        """ログレベルを動的に変更"""
        new_level = self._get_log_level(level_str)
        self.logger.setLevel(new_level)
        for handler in self.logger.handlers:
            handler.setLevel(new_level)
    
    def add_file_handler(self, file_path: str, level: str = "INFO") -> None:
        """追加のファイルハンドラーを追加"""
        try:
            # ディレクトリを作成
            log_dir = os.path.dirname(file_path)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            
            handler = logging.FileHandler(file_path, encoding='utf-8')
            handler.setLevel(self._get_log_level(level))
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            
            self.logger.addHandler(handler)
        except Exception as e:
            self.logger.error(f"ファイルハンドラーの追加に失敗しました: {e}")
    
    def log_system_info(self) -> None:
        """システム情報をログに記録"""
        import sys
        import platform
        
        self.logger.info("=" * 50)
        self.logger.info("Google Search Tool - システム情報")
        self.logger.info("=" * 50)
        self.logger.info(f"Python バージョン: {sys.version}")
        self.logger.info(f"プラットフォーム: {platform.platform()}")
        self.logger.info(f"ログファイル: {self.log_file_path}")
        self.logger.info(f"ログレベル: {logging.getLevelName(self.log_level)}")
        self.logger.info("=" * 50)


def setup_logger_from_config(config_manager) -> logging.Logger:
    """
    設定管理クラスからロガーをセットアップ
    
    Args:
        config_manager: ConfigManagerのインスタンス
        
    Returns:
        設定されたロガー
    """
    logger_config = LoggerConfig(
        log_file_path=config_manager.get_log_file_path(),
        log_level=config_manager.get_log_level(),
        console_output=config_manager.get_console_output()
    )
    
    logger = logger_config.get_logger()
    logger_config.log_system_info()
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    ロガーを取得するユーティリティ関数
    
    Args:
        name: ロガー名（省略時は 'google_search_tool'）
        
    Returns:
        ロガーインスタンス
    """
    if name is None:
        name = 'google_search_tool'
    
    logger = logging.getLogger(name)
    
    # ロガーが設定されていない場合はデフォルト設定を適用
    if not logger.handlers:
        logger_config = LoggerConfig()
        return logger_config.get_logger()
    
    return logger


if __name__ == "__main__":
    # テスト実行
    print("ログ設定のテストを実行中...")
    
    # デフォルト設定でログ設定を作成
    logger_config = LoggerConfig()
    logger = logger_config.get_logger()
    
    # テストログを出力
    logger.debug("これはDEBUGレベルのログです")
    logger.info("これはINFOレベルのログです")
    logger.warning("これはWARNINGレベルのログです")
    logger.error("これはERRORレベルのログです")
    logger.critical("これはCRITICALレベルのログです")
    
    print(f"ログファイルが作成されました: {logger_config.log_file_path}")
    print("ログ設定のテスト完了")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ログ設定モジュール
ファイル出力とコンソール出力の設定、ログレベル管理機能を提供
"""

import logging
import logging.handlers
import os
import threading
import queue
import time
from pathlib import Path
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor


class AsyncLogHandler(logging.Handler):
    """非同期ログハンドラー - ログ出力をバックグラウンドで処理"""
    
    def __init__(self, target_handler: logging.Handler, queue_size: int = 1000):
        """
        非同期ログハンドラーの初期化
        
        Args:
            target_handler: 実際のログ出力を行うハンドラー
            queue_size: ログメッセージキューの最大サイズ
        """
        super().__init__()
        self.target_handler = target_handler
        self.log_queue = queue.Queue(maxsize=queue_size)
        self.worker_thread = None
        self.stop_event = threading.Event()
        self.is_running = False
        
        # バッファリング設定
        self.buffer = []
        self.buffer_size = 100  # バッファに蓄積するログ数
        self.buffer_timeout = 1.0  # バッファのフラッシュ間隔（秒）
        self.last_flush_time = time.time()
        
    def start(self):
        """非同期ログ処理を開始"""
        if not self.is_running:
            self.is_running = True
            self.stop_event.clear()
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
    
    def stop(self, timeout: float = 5.0):
        """非同期ログ処理を停止"""
        if self.is_running:
            self.stop_event.set()
            
            # 残りのログをフラッシュ
            self._flush_buffer()
            
            # ワーカースレッドの終了を待機
            if self.worker_thread and self.worker_thread.is_alive():
                self.worker_thread.join(timeout=timeout)
            
            self.is_running = False
    
    def emit(self, record: logging.LogRecord):
        """ログレコードをキューに追加（非ブロッキング）"""
        if not self.is_running:
            self.start()
        
        try:
            # キューが満杯の場合は古いログを破棄
            if self.log_queue.full():
                try:
                    self.log_queue.get_nowait()
                except queue.Empty:
                    pass
            
            self.log_queue.put_nowait(record)
        except queue.Full:
            # キューが満杯の場合はログを破棄（ブロッキングを防ぐ）
            pass
    
    def _worker(self):
        """バックグラウンドでログ処理を実行するワーカー"""
        while not self.stop_event.is_set() or not self.log_queue.empty():
            try:
                # タイムアウト付きでログレコードを取得
                record = self.log_queue.get(timeout=0.1)
                self.buffer.append(record)
                
                # バッファがいっぱいまたはタイムアウトでフラッシュ
                current_time = time.time()
                if (len(self.buffer) >= self.buffer_size or 
                    current_time - self.last_flush_time >= self.buffer_timeout):
                    self._flush_buffer()
                    
            except queue.Empty:
                # タイムアウトでもフラッシュをチェック
                current_time = time.time()
                if (self.buffer and 
                    current_time - self.last_flush_time >= self.buffer_timeout):
                    self._flush_buffer()
                continue
            except Exception as e:
                # エラーをコンソールに出力（無限ループを防ぐ）
                print(f"AsyncLogHandler worker error: {e}")
        
        # 最終フラッシュ
        self._flush_buffer()
    
    def _flush_buffer(self):
        """バッファ内のログを実際のハンドラーに出力"""
        if not self.buffer:
            return
        
        try:
            for record in self.buffer:
                self.target_handler.emit(record)
            
            # ハンドラーをフラッシュ
            if hasattr(self.target_handler, 'flush'):
                self.target_handler.flush()
                
        except Exception as e:
            print(f"AsyncLogHandler flush error: {e}")
        finally:
            self.buffer.clear()
            self.last_flush_time = time.time()


class OptimizedLogFilter(logging.Filter):
    """最適化されたログフィルター - レベルによる高速フィルタリング"""
    
    def __init__(self, min_level: int = logging.INFO):
        """
        最適化されたログフィルターの初期化
        
        Args:
            min_level: 最小ログレベル
        """
        super().__init__()
        self.min_level = min_level
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        ログレコードをフィルタリング（高速化）
        
        Args:
            record: ログレコード
            
        Returns:
            フィルタを通すかどうか
        """
        # 高速な数値比較でフィルタリング
        return record.levelno >= self.min_level


class LoggerConfig:
    """ログ設定クラス"""
    
    def __init__(self, 
                 log_file_path: str = "logs/search.log",
                 log_level: str = "INFO",
                 console_output: bool = True,
                 max_file_size: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5,
                 async_logging: bool = True,
                 buffer_size: int = 100,
                 queue_size: int = 1000):
        """
        ログ設定クラスの初期化
        
        Args:
            log_file_path: ログファイルのパス
            log_level: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
            console_output: コンソール出力の有無
            max_file_size: ログファイルの最大サイズ（バイト）
            backup_count: バックアップファイル数
            async_logging: 非同期ログ出力を使用するかどうか
            buffer_size: バッファサイズ（非同期ログ用）
            queue_size: キューサイズ（非同期ログ用）
        """
        self.log_file_path = log_file_path
        self.log_level = self._get_log_level(log_level)
        self.console_output = console_output
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.async_logging = async_logging
        self.buffer_size = buffer_size
        self.queue_size = queue_size
        
        # 非同期ハンドラーのリスト
        self.async_handlers = []
        
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
            'CRITICAL': logging.CRITICAL        }
        return level_mapping.get(level_str.upper(), logging.INFO)
    
    def _setup_logger(self) -> logging.Logger:
        """ロガーをセットアップ（非同期対応）"""
        logger = logging.getLogger('google_search_tool')
        logger.setLevel(self.log_level)
        
        # 既存のハンドラーをクリア（非同期ハンドラーも停止）
        self._cleanup_handlers()
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # 最適化されたフィルターを追加
        log_filter = OptimizedLogFilter(self.log_level)
        logger.addFilter(log_filter)
        
        # フォーマッターを作成
        formatter = self._create_formatter()
        
        # ファイルハンドラーを作成
        file_handler = self._create_file_handler()
        file_handler.setFormatter(formatter)
        
        if self.async_logging:
            # 非同期ファイルハンドラーを作成
            async_file_handler = AsyncLogHandler(file_handler, self.queue_size)
            async_file_handler.buffer_size = self.buffer_size
            async_file_handler.setLevel(self.log_level)
            logger.addHandler(async_file_handler)
            self.async_handlers.append(async_file_handler)
            async_file_handler.start()
        else:
            # 同期ファイルハンドラーを追加
            file_handler.setLevel(self.log_level)
            logger.addHandler(file_handler)
        
        # コンソールハンドラーを追加
        if self.console_output:
            console_handler = self._create_console_handler()
            console_handler.setFormatter(formatter)
            
            if self.async_logging:
                # 非同期コンソールハンドラーを作成
                async_console_handler = AsyncLogHandler(console_handler, self.queue_size)
                async_console_handler.buffer_size = min(self.buffer_size, 50)  # コンソールは小さめのバッファ
                async_console_handler.setLevel(self.log_level)
                logger.addHandler(async_console_handler)
                self.async_handlers.append(async_console_handler)
                async_console_handler.start()
            else:
                # 同期コンソールハンドラーを追加
                console_handler.setLevel(self.log_level)
                logger.addHandler(console_handler)
        
        return logger
    
    def _cleanup_handlers(self):
        """非同期ハンドラーをクリーンアップ"""
        for handler in self.async_handlers:
            if isinstance(handler, AsyncLogHandler):
                handler.stop()
        self.async_handlers.clear()
    
    def _create_formatter(self) -> logging.Formatter:
        """ログフォーマッターを作成"""
        return logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def _create_file_handler(self) -> logging.Handler:
        """ファイルハンドラーを作成"""
        return logging.handlers.RotatingFileHandler(
            self.log_file_path,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
    
    def _create_console_handler(self) -> logging.Handler:
        """コンソールハンドラーを作成"""
        return logging.StreamHandler()
    
    def shutdown(self):
        """ロガーをシャットダウン（非同期ハンドラーを停止）"""
        self._cleanup_handlers()
        logging.shutdown()
    
    def flush(self):
        """すべてのハンドラーをフラッシュ"""
        for handler in self.async_handlers:
            if isinstance(handler, AsyncLogHandler):
                handler._flush_buffer()
    
    def get_logger(self) -> logging.Logger:
        """設定済みロガーを取得"""
        return self.logger
    
    def set_level(self, level: str):
        """ログレベルを動的に変更"""
        new_level = self._get_log_level(level)
        self.log_level = new_level
        self.logger.setLevel(new_level)
        
        # すべてのハンドラーのレベルも更新
        for handler in self.logger.handlers:
            handler.setLevel(new_level)
    
    def enable_async_logging(self):
        """非同期ログを有効化"""
        if not self.async_logging:
            self.async_logging = True
            self.logger = self._setup_logger()
    
    def disable_async_logging(self):
        """非同期ログを無効化"""
        if self.async_logging:
            self.async_logging = False
            self.logger = self._setup_logger()
    
    def get_log_stats(self) -> dict:
        """ログ統計情報を取得"""
        stats = {
            'log_level': logging.getLevelName(self.log_level),
            'async_logging': self.async_logging,
            'handlers_count': len(self.logger.handlers),
            'async_handlers_count': len(self.async_handlers)
        }
        
        # 非同期ハンドラーの統計
        for i, handler in enumerate(self.async_handlers):
            if isinstance(handler, AsyncLogHandler):
                stats[f'async_handler_{i}'] = {
                    'queue_size': handler.log_queue.qsize(),
                    'buffer_size': len(handler.buffer),
                    'is_running': handler.is_running
                }
        
        return stats


def setup_logger_from_config(config_manager, async_logging: bool = True) -> logging.Logger:
    """
    設定管理クラスから非同期ログ設定を作成
    
    Args:
        config_manager: ConfigManagerのインスタンス
        async_logging: 非同期ログを使用するかどうか
        
    Returns:
        設定済みロガー
    """
    logger_config = LoggerConfig(
        log_file_path=config_manager.get_log_file_path(),
        log_level=config_manager.get_log_level(),
        console_output=config_manager.get_console_output(),
        async_logging=async_logging,
        buffer_size=100,  # デフォルトバッファサイズ
        queue_size=1000   # デフォルトキューサイズ
    )
    
    return logger_config.get_logger()


def create_performance_logger(log_file: str = "logs/performance.log", 
                            async_logging: bool = True) -> logging.Logger:
    """
    パフォーマンス測定用の専用ロガーを作成
    
    Args:
        log_file: ログファイルパス
        async_logging: 非同期ログを使用するかどうか
        
    Returns:
        パフォーマンス測定用ロガー
    """
    logger_config = LoggerConfig(
        log_file_path=log_file,
        log_level="DEBUG",
        console_output=False,  # パフォーマンスログはファイルのみ
        async_logging=async_logging,
        buffer_size=200,  # 大きめのバッファ
        queue_size=2000   # 大きめのキュー
    )
    
    return logger_config.get_logger()


class PerformanceLogger:
    """パフォーマンス測定用ロガークラス"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.timers = {}
    
    def start_timer(self, name: str):
        """タイマーを開始"""
        self.timers[name] = time.time()
        self.logger.debug(f"Timer started: {name}")
    
    def end_timer(self, name: str) -> float:
        """タイマーを終了し、経過時間を記録"""
        if name in self.timers:
            elapsed = time.time() - self.timers[name]
            self.logger.info(f"Timer {name}: {elapsed:.4f}s")
            del self.timers[name]
            return elapsed
        else:
            self.logger.warning(f"Timer {name} not found")
            return 0.0
    
    def log_memory_usage(self, context: str = ""):
        """メモリ使用量をログ出力"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            self.logger.info(f"Memory usage{' (' + context + ')' if context else ''}: "
                           f"RSS={memory_info.rss / 1024 / 1024:.1f}MB, "
                           f"VMS={memory_info.vms / 1024 / 1024:.1f}MB")
        except ImportError:
            self.logger.warning("psutil not available for memory monitoring")


if __name__ == "__main__":
    # テスト実行
    import sys
    import os
    
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        from config_manager import ConfigManager
        
        # 設定を読み込み
        config = ConfigManager(skip_validation=True)
        
        print("非同期ログのテストを実行中...")
        
        # 非同期ロガーを作成
        logger = setup_logger_from_config(config, async_logging=True)
        
        # パフォーマンステスト
        import time
        start_time = time.time()
        
        # 大量のログ出力テスト
        for i in range(1000):
            logger.info(f"非同期ログテスト {i}")
        
        end_time = time.time()
        
        print(f"✅ 1000件のログ出力時間: {end_time - start_time:.4f}秒")
        
        # パフォーマンスロガーのテスト
        perf_logger = create_performance_logger()
        perf_monitor = PerformanceLogger(perf_logger)
        
        perf_monitor.start_timer("test_operation")
        time.sleep(0.1)  # 処理のシミュレーション
        elapsed = perf_monitor.end_timer("test_operation")
        
        print(f"✅ パフォーマンス測定テスト: {elapsed:.4f}秒")
        
        # ログ統計の表示
        if hasattr(logger, 'handlers'):
            for handler in logger.handlers:
                if isinstance(handler, AsyncLogHandler):
                    print(f"✅ 非同期ハンドラー統計:")
                    print(f"   キューサイズ: {handler.log_queue.qsize()}")
                    print(f"   バッファサイズ: {len(handler.buffer)}")
                    print(f"   動作状態: {handler.is_running}")
        
        print("✅ 非同期ログテスト完了")
        
        # クリーンアップ
        time.sleep(1)  # 非同期処理の完了を待機
        
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()

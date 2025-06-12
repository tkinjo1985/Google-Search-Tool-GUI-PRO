#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV出力モジュール
検索結果をCSV形式で出力する機能を提供
"""

import csv
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from search_result import SearchResult


class CSVWriter:
    """CSV出力クラス"""
    
    def __init__(self, output_directory: str = "output", 
                 filename_prefix: str = "search_results",
                 encoding: str = "utf-8-sig"):  # BOM付きUTF-8
        """
        CSV出力クラスの初期化
        
        Args:
            output_directory: 出力ディレクトリ
            filename_prefix: ファイル名のプレフィックス
            encoding: 文字エンコーディング
        """
        self.output_directory = output_directory
        self.filename_prefix = filename_prefix
        self.encoding = encoding
        self.logger = logging.getLogger('google_search_tool.csv_writer')
        
        # 出力ディレクトリを作成
        self._ensure_output_directory()
    
    def _ensure_output_directory(self) -> None:
        """出力ディレクトリが存在することを確認し、必要に応じて作成"""
        try:
            os.makedirs(self.output_directory, exist_ok=True)
            self.logger.debug(f"出力ディレクトリを確認/作成: {self.output_directory}")
        except Exception as e:
            self.logger.error(f"出力ディレクトリの作成に失敗: {e}")
            raise CSVWriterError(f"出力ディレクトリの作成に失敗しました: {e}")
    
    def _check_disk_space(self, estimated_size: int = 1024 * 1024) -> bool:
        """
        ディスク容量をチェック
        
        Args:
            estimated_size: 推定ファイルサイズ（バイト）
            
        Returns:
            十分な容量がある場合True
        """
        try:
            stat = os.statvfs(self.output_directory)
            available_space = stat.f_bavail * stat.f_frsize
            
            if available_space < estimated_size * 2:  # 余裕を持って2倍のサイズをチェック
                self.logger.warning(f"ディスク容量不足の可能性: 利用可能={available_space//1024//1024}MB")
                return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"ディスク容量チェックに失敗: {e}")
            return True  # チェックできない場合は続行
    
    def _check_file_permissions(self, file_path: str) -> bool:
        """
        ファイル書き込み権限をチェック
        
        Args:
            file_path: チェックするファイルパス
            
        Returns:
            書き込み可能な場合True
        """
        try:
            # ディレクトリの書き込み権限をチェック
            directory = os.path.dirname(file_path)
            if not os.access(directory, os.W_OK):
                self.logger.error(f"ディレクトリに書き込み権限がありません: {directory}")
                return False
            
            # ファイルが存在する場合は上書き権限をチェック
            if os.path.exists(file_path):
                if not os.access(file_path, os.W_OK):
                    self.logger.error(f"ファイルに書き込み権限がありません: {file_path}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"権限チェックに失敗: {e}")
            return False
    
    def generate_filename(self, suffix: str = "", timestamp: datetime = None) -> str:
        """
        ファイル名を生成
        
        Args:
            suffix: ファイル名のサフィックス
            timestamp: タイムスタンプ（省略時は現在時刻）
            
        Returns:
            生成されたファイル名
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        
        if suffix:
            filename = f"{self.filename_prefix}_{suffix}_{timestamp_str}.csv"
        else:
            filename = f"{self.filename_prefix}_{timestamp_str}.csv"
        
        return filename
    
    def get_output_path(self, filename: str = None) -> str:
        """
        出力ファイルの完全パスを取得
        
        Args:
            filename: ファイル名（省略時は自動生成）
            
        Returns:
            出力ファイルの完全パス
        """
        if filename is None:
            filename = self.generate_filename()
        
        return os.path.join(self.output_directory, filename)
    
    def _prevent_overwrite(self, file_path: str) -> str:
        """
        ファイルの上書きを防ぐために、必要に応じてファイル名を変更
        
        Args:
            file_path: 元のファイルパス
            
        Returns:
            重複を避けたファイルパス
        """
        if not os.path.exists(file_path):
            return file_path
        
        base_path, ext = os.path.splitext(file_path)
        counter = 1
        
        while True:
            new_path = f"{base_path}_{counter:03d}{ext}"
            if not os.path.exists(new_path):
                self.logger.info(f"ファイル名を変更して重複を回避: {os.path.basename(new_path)}")
                return new_path
            counter += 1
            
            if counter > 999:  # 無限ループを防ぐ
                raise CSVWriterError("ファイル名の重複回避に失敗しました")
    
    def write_results(self, results: List[SearchResult], 
                     filename: str = None, 
                     prevent_overwrite: bool = True) -> str:
        """
        検索結果をCSVファイルに書き込み
        
        Args:
            results: 検索結果のリスト
            filename: 出力ファイル名（省略時は自動生成）
            prevent_overwrite: 上書き防止フラグ
            
        Returns:
            作成されたファイルのパス
        """
        if not results:
            self.logger.warning("書き込む検索結果がありません")
            return ""
        
        # ファイルパスを決定
        output_path = self.get_output_path(filename)
        
        if prevent_overwrite:
            output_path = self._prevent_overwrite(output_path)
        
        # 権限とディスク容量をチェック
        if not self._check_file_permissions(output_path):
            raise CSVWriterError(f"ファイル書き込み権限がありません: {output_path}")
        
        estimated_size = len(results) * 500  # 1行あたり約500バイトと仮定
        if not self._check_disk_space(estimated_size):
            self.logger.warning("ディスク容量が不足している可能性があります")
        
        try:
            self.logger.info(f"CSV出力開始: {output_path} ({len(results)}件)")
            
            with open(output_path, 'w', newline='', encoding=self.encoding) as csvfile:
                writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
                
                # ヘッダー行を書き込み
                headers = SearchResult.get_csv_headers()
                writer.writerow(headers)
                
                # データ行を書き込み
                for i, result in enumerate(results, 1):
                    try:
                        row = result.to_csv_row()
                        writer.writerow(row)
                        
                        if i % 100 == 0:  # 100件ごとに進捗をログ
                            self.logger.debug(f"CSV書き込み進捗: {i}/{len(results)}件")
                            
                    except Exception as e:
                        self.logger.error(f"行の書き込みエラー (行{i}): {e}")
                        # 個別の行エラーは無視して続行
                        continue
            
            # ファイルサイズを確認
            file_size = os.path.getsize(output_path)
            self.logger.info(f"CSV出力完了: {output_path} ({file_size:,} bytes)")
            
            return output_path
            
        except Exception as e:
            self.logger.error(f"CSV出力エラー: {e}")
            # 失敗した場合は不完全なファイルを削除
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                    self.logger.info("不完全なファイルを削除しました")
                except:
                    pass
            
            raise CSVWriterError(f"CSV出力に失敗しました: {e}")
    
    def write_results_streaming(self, results: List[SearchResult], 
                               filename: str = None,
                               prevent_overwrite: bool = True,
                               batch_size: int = 1000) -> str:
        """
        検索結果をストリーミング処理でCSV形式で出力（大量データ対応）
        
        Args:
            results: 検索結果のリスト
            filename: 出力ファイル名（省略時は自動生成）
            prevent_overwrite: 既存ファイルの上書きを防ぐかどうか
            batch_size: バッチ処理サイズ
            
        Returns:
            作成されたCSVファイルのパス
        """
        if not results:
            self.logger.warning("書き込む検索結果がありません")
            return ""
        
        # ファイル名の生成
        if filename is None:
            filename = self.generate_filename("streaming")
          # 重複ファイル名チェック
        file_path = os.path.join(self.output_directory, filename)
        if prevent_overwrite:
            file_path = self._prevent_overwrite(file_path)
        
        # 権限チェック
        if not self._check_file_permissions(file_path):
            raise CSVWriterError(f"ファイル書き込み権限がありません: {file_path}")
          # 推定ファイルサイズでディスク容量チェック
        estimated_size = len(results) * 500  # 1行あたり約500バイトと推定
        if not self._check_disk_space(estimated_size):
            self.logger.warning("ディスク容量が不足している可能性があります")
        
        try:
            self.logger.info(f"ストリーミングCSV出力開始: {file_path} ({len(results):,} 件)")
            
            # バッファサイズを最適化（64KB）
            buffer_size = 64 * 1024
            
            with open(file_path, 'w', newline='', encoding=self.encoding, buffering=buffer_size) as csvfile:
                writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
                
                # ヘッダー行を書き込み（標準書き込みと同じヘッダーを使用）
                headers = SearchResult.get_csv_headers()
                writer.writerow(headers)
                
                # バッチ処理でデータを書き込み
                batch = []
                processed_count = 0
                
                for i, result in enumerate(results):
                    # SearchResultの標準的なCSV行データを使用
                    row_data = result.to_csv_row()
                    batch.append(row_data)
                    
                    # バッチサイズに達したら書き込み
                    if len(batch) >= batch_size:
                        writer.writerows(batch)
                        csvfile.flush()  # バッファを強制的にフラッシュ
                        processed_count += len(batch)
                        batch = []
                        
                        # 進捗ログ（10000行ごと）
                        if processed_count % 10000 == 0:
                            self.logger.info(f"ストリーミング進捗: {processed_count:,} / {len(results):,} 行処理済み")
                
                # 残りのバッチを書き込み
                if batch:
                    writer.writerows(batch)
                    csvfile.flush()
                    processed_count += len(batch)
                
                self.logger.info(f"ストリーミングCSV出力完了: {processed_count:,} 行処理")
            
            return file_path
            
        except Exception as e:
            self.logger.error(f"ストリーミングCSV出力エラー: {e}")
            # エラー時はファイルを削除
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
            raise CSVWriterError(f"ストリーミングCSV出力に失敗しました: {e}")
    
    def write_results_optimized(self, results: List[SearchResult], 
                               filename: str = None,
                               prevent_overwrite: bool = True) -> str:
        """
        最適化された検索結果CSV出力（データサイズに応じて処理方法を選択）
        
        Args:
            results: 検索結果のリスト
            filename: 出力ファイル名（省略時は自動生成）
            prevent_overwrite: 既存ファイルの上書きを防ぐかどうか
            
        Returns:
            作成されたCSVファイルのパス
        """
        if not results:
            self.logger.warning("書き込む検索結果がありません")
            return ""
        
        # データサイズに応じて処理方法を選択
        if len(results) > 1000:
            self.logger.info(f"大量データです。ストリーミング処理を使用します ({len(results):,} 件)")
            return self.write_results_streaming(results, filename, prevent_overwrite)
        else:
            self.logger.info(f"標準処理を使用します ({len(results):,} 件)")
            return self.write_results(results, filename, prevent_overwrite)

    def append_result(self, result: SearchResult, filename: str) -> bool:
        """
        既存のCSVファイルに検索結果を追加
        
        Args:
            result: 追加する検索結果
            filename: 対象ファイル名
            
        Returns:
            成功した場合True
        """
        file_path = os.path.join(self.output_directory, filename)
        
        if not os.path.exists(file_path):
            self.logger.error(f"追加対象ファイルが存在しません: {file_path}")
            return False
        
        try:
            with open(file_path, 'a', newline='', encoding=self.encoding) as csvfile:
                writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
                row = result.to_csv_row()
                writer.writerow(row)
            
            self.logger.debug(f"CSVに結果を追加: {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"CSV追加エラー: {e}")
            return False
    
    def create_summary_file(self, results: List[SearchResult], 
                           stats: Dict[str, Any], 
                           filename: str = None) -> str:
        """
        検索結果のサマリーファイルを作成
        
        Args:
            results: 検索結果のリスト
            stats: 検索統計情報
            filename: サマリーファイル名
            
        Returns:
            作成されたサマリーファイルのパス
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"search_summary_{timestamp}.txt"
        
        summary_path = os.path.join(self.output_directory, filename)
        
        try:
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write("Google Search Tool - 検索結果サマリー\n")
                f.write("=" * 50 + "\n\n")
                
                # 統計情報
                f.write("検索統計:\n")
                f.write(f"  総検索数: {stats.get('total_searches', 0)}\n")
                f.write(f"  成功数: {stats.get('successful_searches', 0)}\n")
                f.write(f"  失敗数: {stats.get('failed_searches', 0)}\n")
                f.write(f"  成功率: {stats.get('success_rate', 0):.1f}%\n\n")
                
                # 結果一覧
                f.write("検索結果一覧:\n")
                for i, result in enumerate(results, 1):
                    f.write(f"{i:3d}. {result.search_query}\n")
                    f.write(f"     {result.title}\n")
                    f.write(f"     {result.url}\n")
                    f.write(f"     {result.get_domain()}\n\n")
                
                # 実行時刻
                f.write(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            self.logger.info(f"サマリーファイル作成完了: {summary_path}")
            return summary_path
            
        except Exception as e:
            self.logger.error(f"サマリーファイル作成エラー: {e}")
            raise CSVWriterError(f"サマリーファイルの作成に失敗しました: {e}")


class CSVWriterError(Exception):
    """CSV出力関連のエラー"""
    pass


def create_csv_writer_from_config(config_manager) -> CSVWriter:
    """
    設定管理クラスからCSV出力クラスを作成
    
    Args:
        config_manager: ConfigManagerのインスタンス
        
    Returns:
        設定されたCSV出力クラス
    """
    return CSVWriter(
        output_directory=config_manager.get_output_directory(),
        filename_prefix=config_manager.get_output_filename_prefix()
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
        
        # CSV出力クラスを作成
        csv_writer = create_csv_writer_from_config(config)
        
        print("CSV出力のテストを実行中...")
        
        # テスト用のSearchResultを作成
        test_results = []
        for i in range(3):
            result = SearchResult(
                title=f"テストタイトル {i+1}",
                url=f"https://example{i+1}.com/test",
                snippet=f"これはテスト用のスニペットです。結果番号: {i+1}",
                search_query=f"テストクエリ {i+1}",
                rank=1
            )
            test_results.append(result)
        
        # CSV出力テスト
        output_file = csv_writer.write_results(test_results, "test_output.csv")
        
        if output_file and os.path.exists(output_file):
            print(f"✅ CSV出力テスト成功: {output_file}")
            
            # ファイルサイズを確認
            file_size = os.path.getsize(output_file)
            print(f"   ファイルサイズ: {file_size} bytes")
            
            # サマリーファイルのテスト
            test_stats = {
                'total_searches': 3,
                'successful_searches': 3,
                'failed_searches': 0,
                'success_rate': 100.0
            }
            
            summary_file = csv_writer.create_summary_file(test_results, test_stats, "test_summary.txt")
            if summary_file and os.path.exists(summary_file):
                print(f"✅ サマリーファイル作成成功: {summary_file}")
            else:
                print("❌ サマリーファイル作成失敗")
        else:
            print("❌ CSV出力テスト失敗")
        
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")

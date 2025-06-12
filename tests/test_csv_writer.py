#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV出力テスト
CSVWriterクラスのファイル作成、文字エンコーディング、データ形式テスト
"""

import unittest
import tempfile
import os
import csv
import shutil
from datetime import datetime
from unittest.mock import patch, mock_open
import sys

# プロジェクトのsrcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.csv_writer import CSVWriter, CSVWriterError
from src.search_result import SearchResult


class TestCSVWriter(unittest.TestCase):
    """CSVWriterのテストクラス"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.csv_writer = CSVWriter(
            output_directory=self.temp_dir,
            filename_prefix="test_results"
        )
        
        # テスト用検索結果を作成
        self.test_results = [
            SearchResult(
                title="テストタイトル1",
                url="https://example1.com",
                snippet="これはテストスニペット1です。",
                search_query="テストクエリ1",
                rank=1,
                display_link="example1.com"
            ),
            SearchResult(
                title="テストタイトル2",
                url="https://example2.com",
                snippet="これはテストスニペット2です。",
                search_query="テストクエリ2",
                rank=1,
                display_link="example2.com"
            )
        ]
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        shutil.rmtree(self.temp_dir)
    
    def test_single_result_output(self):
        """単一結果のCSV出力テスト"""
        result = self.test_results[0]
        filename = self.csv_writer.write_results([result])
        
        # ファイルが作成されたことを確認
        self.assertTrue(os.path.exists(filename))
        
        # ファイル内容を確認
        with open(filename, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # 1行のデータがあることを確認
            self.assertEqual(len(rows), 1)
            row = rows[0]
            
            # データ内容を確認
            self.assertEqual(row['検索キーワード'], "テストクエリ1")
            self.assertEqual(row['タイトル'], "テストタイトル1")
            self.assertEqual(row['URL'], "https://example1.com")
            self.assertEqual(row['スニペット'], "これはテストスニペット1です。")
            self.assertEqual(row['順位'], "1")
            self.assertEqual(row['ドメイン'], "example1.com")
    
    def test_multiple_results_output(self):
        """複数結果のCSV出力テスト"""
        filename = self.csv_writer.write_results(self.test_results)
        
        # ファイルが作成されたことを確認
        self.assertTrue(os.path.exists(filename))
        
        # ファイル内容を確認
        with open(filename, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # 2行のデータがあることを確認
            self.assertEqual(len(rows), 2)
            
            # 1行目のデータを確認
            self.assertEqual(rows[0]['検索キーワード'], "テストクエリ1")
            self.assertEqual(rows[0]['タイトル'], "テストタイトル1")
            
            # 2行目のデータを確認
            self.assertEqual(rows[1]['検索キーワード'], "テストクエリ2")
            self.assertEqual(rows[1]['タイトル'], "テストタイトル2")
    
    def test_filename_generation(self):
        """ファイル名生成のテスト"""
        import time
        
        # タイムスタンプ付きファイル名が生成されることを確認
        filename1 = self.csv_writer.generate_filename()
        time.sleep(0.001)  # 1ミリ秒待機して確実に異なるファイル名を生成
        filename2 = self.csv_writer.generate_filename()
        
        # プレフィックスが含まれていることを確認
        self.assertIn("test_results", filename1)
        self.assertIn("test_results", filename2)
        
        # 拡張子が正しいことを確認
        self.assertTrue(filename1.endswith('.csv'))
        self.assertTrue(filename2.endswith('.csv'))
        
        # サフィックス付きファイル名のテスト
        filename_with_suffix = self.csv_writer.generate_filename("batch")
        self.assertIn("batch", filename_with_suffix)
    
    def test_special_characters_handling(self):
        """特殊文字の処理テスト"""
        # 特殊文字を含む検索結果を作成
        special_result = SearchResult(
            title="特殊文字テスト: \"引用符\" & アンパサンド < > タグ",
            url="https://example.com/special?param=value&other=データ",
            snippet="改行を含む\nスニペット\nです。\r\nWindows形式も。",
            search_query="特殊文字,カンマ;セミコロン\"引用符\"",
            rank=1
        )
        
        filename = self.csv_writer.write_results([special_result])
        
        # ファイル内容を確認
        with open(filename, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            row = rows[0]
            
            # 特殊文字が適切にエスケープされていることを確認
            self.assertIn("引用符", row['タイトル'])
            self.assertIn("アンパサンド", row['タイトル'])
            self.assertIn("改行を含む", row['スニペット'])
            
            # CSVとして正しく読み込めることを確認
            self.assertEqual(len(rows), 1)
    
    def test_encoding_utf8_bom(self):
        """UTF-8 BOMエンコーディングのテスト"""
        result = self.test_results[0]
        filename = self.csv_writer.write_results([result])
        
        # ファイルをバイナリモードで読み取り、BOMを確認
        with open(filename, 'rb') as f:
            content = f.read()
            
            # UTF-8 BOMが存在することを確認
            self.assertTrue(content.startswith(b'\xef\xbb\xbf'))
    
    def test_directory_creation(self):
        """ディレクトリ自動作成のテスト"""
        # 存在しないディレクトリでCSVWriterを作成
        nonexistent_dir = os.path.join(self.temp_dir, 'new_dir', 'sub_dir')
        csv_writer = CSVWriter(output_directory=nonexistent_dir)
        
        # ディレクトリが作成されることを確認
        self.assertTrue(os.path.exists(nonexistent_dir))
    
    def test_file_overwrite_prevention(self):
        """ファイル上書き防止のテスト"""
        result = self.test_results[0]
        
        # 同じファイル名で2回書き込み
        with patch.object(self.csv_writer, 'generate_filename', return_value='fixed_name.csv'):
            filename1 = self.csv_writer.write_results([result])
            filename2 = self.csv_writer.write_results([result])
            
            # 異なるファイル名が生成されることを確認
            self.assertNotEqual(filename1, filename2)
            
            # 両方のファイルが存在することを確認
            self.assertTrue(os.path.exists(filename1))
            self.assertTrue(os.path.exists(filename2))
    
    def test_empty_results_handling(self):
        """空の結果リストの処理テスト"""
        filename = self.csv_writer.write_results([])
        
        # 空のリストの場合は空文字列が返されることを確認
        self.assertEqual(filename, "")
    
    def test_large_dataset(self):
        """大量データの処理テスト"""
        # 100個の検索結果を作成
        large_results = []
        for i in range(100):
            result = SearchResult(
                title=f"大量データテスト{i}",
                url=f"https://example{i}.com",
                snippet=f"これは{i}番目のテストデータです。",
                search_query=f"クエリ{i}",
                rank=1
            )
            large_results.append(result)
        
        filename = self.csv_writer.write_results(large_results)
        
        # ファイルが作成されることを確認
        self.assertTrue(os.path.exists(filename))
        
        # 全データが書き込まれることを確認
        with open(filename, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 100)
            
            # 最初と最後のデータを確認
            self.assertEqual(rows[0]['タイトル'], "大量データテスト0")
            self.assertEqual(rows[99]['タイトル'], "大量データテスト99")
    
    def test_invalid_directory_handling(self):
        """不正なディレクトリのハンドリングテスト"""
        # 権限がないディレクトリを指定（読み取り専用ファイルを作成してシミュレート）
        readonly_file = os.path.join(self.temp_dir, 'readonly_file')
        with open(readonly_file, 'w') as f:
            f.write("test")
        
        # ファイルと同じ名前のディレクトリを作成しようとしてエラーを発生させる
        with self.assertRaises(CSVWriterError):
            CSVWriter(output_directory=readonly_file)
    
    def test_header_fields(self):
        """ヘッダーフィールドのテスト"""
        result = self.test_results[0]
        filename = self.csv_writer.write_results([result])
        
        # ヘッダーフィールドを確認
        with open(filename, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            expected_headers = [
                '検索キーワード', 'タイトル', 'URL', 'スニペット', 
                '順位', 'ドメイン', '検索日時'
            ]
            
            for header in expected_headers:
                self.assertIn(header, reader.fieldnames)
    
    def test_datetime_formatting(self):
        """日時フォーマットのテスト"""
        result = self.test_results[0]
        filename = self.csv_writer.write_results([result])
        
        # 日時フォーマットを確認
        with open(filename, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            datetime_str = rows[0]['検索日時']
            
            # 日時文字列が期待される形式であることを確認
            try:
                parsed_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
                self.assertIsInstance(parsed_datetime, datetime)
            except ValueError:
                self.fail(f"日時フォーマットが不正です: {datetime_str}")
    
    def test_streaming_write_performance(self):
        """ストリーミング書き込みのパフォーマンステスト"""
        # 大量のテストデータを生成（5000件）
        large_results = []
        for i in range(5000):
            result = SearchResult(
                title=f"大量データテストタイトル{i}",
                url=f"https://example{i}.com",
                snippet=f"これは大量データテスト用のスニペット{i}です。" * 5,
                search_query=f"大量データテストクエリ{i}",
                rank=1,
                display_link=f"example{i}.com"
            )
            large_results.append(result)
        
        # ストリーミング書き込みでファイル作成
        start_time = datetime.now()
        file_path = self.csv_writer.write_results_streaming(large_results)
        end_time = datetime.now()
        
        # ファイルが正常に作成されることを確認
        self.assertTrue(os.path.exists(file_path))
        
        # パフォーマンス測定（5000件を5秒以内に処理できることを確認）
        processing_time = (end_time - start_time).total_seconds()
        self.assertLess(processing_time, 5.0, f"ストリーミング処理が遅すぎます: {processing_time}秒")
        
        # ファイル内容の検証
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        # 正しい件数が書き込まれていることを確認
        self.assertEqual(len(rows), 5000)
          # 先頭と末尾のデータが正しいことを確認
        self.assertEqual(rows[0]['タイトル'], '大量データテストタイトル0')
        self.assertEqual(rows[4999]['タイトル'], '大量データテストタイトル4999')
    
    def test_streaming_vs_standard_consistency(self):
        """ストリーミング書き込みと標準書き込みの一貫性テスト"""
        # 標準書き込みでファイル作成
        standard_file = self.csv_writer.write_results(self.test_results)
        
        # ストリーミング書き込みでファイル作成
        streaming_file = self.csv_writer.write_results_streaming(self.test_results)
        
        # 両ファイルの内容が同じであることを確認
        with open(standard_file, 'r', encoding='utf-8-sig') as f1, \
             open(streaming_file, 'r', encoding='utf-8-sig') as f2:
            standard_content = f1.read()
            streaming_content = f2.read()
            
        self.assertEqual(standard_content, streaming_content)
    
    def test_streaming_batch_processing(self):
        """ストリーミング書き込みのバッチ処理テスト"""
        # 2500件のテストデータ（バッチサイズ1000を想定）
        batch_results = []
        for i in range(2500):
            result = SearchResult(
                title=f"バッチテストタイトル{i}",
                url=f"https://batch{i}.com",
                snippet=f"バッチテスト用スニペット{i}",
                search_query=f"バッチテストクエリ{i}",
                rank=1,
                display_link=f"batch{i}.com"
            )
            batch_results.append(result)
        
        # ストリーミング書き込み実行
        file_path = self.csv_writer.write_results_streaming(batch_results)
        
        # ファイル内容検証
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # 全データが正しく書き込まれていることを確認
        self.assertEqual(len(rows), 2500)
          # バッチ境界のデータが正しいことを確認
        self.assertEqual(rows[999]['タイトル'], 'バッチテストタイトル999')   # 1番目のバッチ最後
        self.assertEqual(rows[1000]['タイトル'], 'バッチテストタイトル1000') # 2番目のバッチ最初
        self.assertEqual(rows[1999]['タイトル'], 'バッチテストタイトル1999') # 2番目のバッチ最後
        self.assertEqual(rows[2000]['タイトル'], 'バッチテストタイトル2000') # 3番目のバッチ最初


if __name__ == '__main__':
    unittest.main()

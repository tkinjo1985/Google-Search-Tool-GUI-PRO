#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Search Tool - GUI版メインアプリケーション
PyQt6を使用したGUIインターフェース
"""

import sys
import os
import threading
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QProgressBar,
    QGroupBox, QFileDialog, QMessageBox, QTabWidget,
    QTableWidget, QTableWidgetItem, QSplitter, QMenuBar,
    QStatusBar, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QFrame
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QAction, QFont, QIcon, QTextCursor

# プロジェクトのsrcディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from search_tool import SearchTool
from config_manager import ConfigManager
from search_result import SearchResult


def get_resource_path(relative_path):
    """PyInstallerでパッケージ化されたリソースファイルのパスを取得"""
    try:
        # PyInstallerの実行時パス（_MEIPASS）
        base_path = sys._MEIPASS
    except AttributeError:
        # 通常のPython実行時
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    return os.path.join(base_path, relative_path)


# アイコンキャッシュ（起動最適化）
_icon_cache = {}

def get_cached_icon(icon_path):
    """アイコンのキャッシュ機能付き取得"""
    if icon_path in _icon_cache:
        return _icon_cache[icon_path]
    
    if os.path.exists(icon_path):
        try:
            icon = QIcon(icon_path)
            _icon_cache[icon_path] = icon
            return icon
        except Exception:
            pass
    
    return None


class SearchWorker(QThread):
    """検索処理を別スレッドで実行するワーカークラス"""
    # シグナル定義
    progress_updated = pyqtSignal(int, str)  # (進捗%, メッセージ)
    result_found = pyqtSignal(dict)  # 検索結果
    search_completed = pyqtSignal(list)  # 全結果
    error_occurred = pyqtSignal(str)  # エラーメッセージ
    
    def __init__(self, keywords: List[str], search_delay: float = 1.0, num_results: int = 1, 
                 search_params: dict = None):
        super().__init__()
        self.keywords = keywords
        self.search_delay = search_delay
        self.num_results = num_results
        self.search_params = search_params or {}
        self.search_tool = None
        self.is_running = True
        
    def run(self):
        """検索実行"""
        try:
            # SearchToolを初期化（GUI用、シグナルハンドラー無効）
            self.search_tool = SearchTool(setup_signals=False)
            if not self.search_tool.initialize_for_gui():
                self.error_occurred.emit("SearchToolの初期化に失敗しました")
                return
            
            # API接続テスト
            if not self.search_tool.test_connection():
                self.error_occurred.emit("API接続テストに失敗しました")
                return
            
            results = []
            total_keywords = len(self.keywords)
            
            for i, keyword in enumerate(self.keywords):
                if not self.is_running:
                    break
                
                # 進捗更新
                progress = int((i / total_keywords) * 100)
                self.progress_updated.emit(progress, f"検索中 ({i+1}/{total_keywords}): {keyword}")
                
                try:                    # 検索実行 - 複数結果対応
                    if self.num_results == 1:
                        # 単一結果の場合
                        result = self.search_tool.search_single_keyword_with_params(keyword, self.search_params)
                        if result:
                            result_dict = {
                                'keyword': keyword,
                                'rank': 1,
                                'title': result.title,
                                'url': result.url,
                                'snippet': result.snippet,
                                'timestamp': result.search_datetime.strftime('%Y-%m-%d %H:%M:%S')
                            }
                            results.append(result_dict)
                            self.result_found.emit(result_dict)
                            self.progress_updated.emit(progress, f"成功 ({i+1}/{total_keywords}): {keyword}")
                        else:
                            self.progress_updated.emit(progress, f"結果なし ({i+1}/{total_keywords}): {keyword}")
                    else:
                        # 複数結果の場合
                        search_results = self.search_tool.search_multiple_keywords_with_params(keyword, self.num_results, self.search_params)
                        if search_results:
                            for rank, result in enumerate(search_results, 1):
                                result_dict = {
                                    'keyword': keyword,
                                    'rank': rank,
                                    'title': result.title,
                                    'url': result.url,
                                    'snippet': result.snippet,
                                    'timestamp': result.search_datetime.strftime('%Y-%m-%d %H:%M:%S')
                                }
                                results.append(result_dict)
                                self.result_found.emit(result_dict)
                            self.progress_updated.emit(progress, f"成功 ({i+1}/{total_keywords}): {keyword} ({len(search_results)}件)")
                        else:
                            self.progress_updated.emit(progress, f"結果なし ({i+1}/{total_keywords}): {keyword}")
                    
                    # 検索間隔の待機
                    if i < total_keywords - 1:  # 最後のキーワードでない場合
                        self.progress_updated.emit(progress, f"待機中... (次: {self.keywords[i+1]})")
                        self.msleep(int(self.search_delay * 1000))
                        
                except Exception as e:
                    error_msg = f"キーワード '{keyword}' の検索でエラー: {str(e)}"
                    self.error_occurred.emit(error_msg)
                    self.progress_updated.emit(progress, f"エラー ({i+1}/{total_keywords}): {keyword}")
            
            # 完了
            self.progress_updated.emit(100, f"検索完了: {len(results)} 件の結果を取得")
            self.search_completed.emit(results)
            
        except Exception as e:
            self.error_occurred.emit(f"検索処理でエラーが発生しました: {str(e)}")
    
    def stop(self):
        """検索停止"""
        self.is_running = False


class GoogleSearchGUI(QMainWindow):
    """Google Search Tool GUIメインクラス"""
    
    def __init__(self):
        super().__init__()
        self.search_worker = None
        self.search_results = []
        self.config_manager = None
        
        self.init_ui()
        self.load_config()
        
    def init_ui(self):
        """UIの初期化（起動最適化済み）"""
        self.setWindowTitle("Google Search Tool - PRO")
        self.setGeometry(100, 100, 1200, 800)
        
        # アイコンを設定（キャッシュ付き）
        icon_path = get_resource_path(os.path.join('icon', 'app_icon.ico'))
        
        cached_icon = get_cached_icon(icon_path)
        if cached_icon:
            self.setWindowIcon(cached_icon)
            print("✅ ウィンドウアイコン設定完了（キャッシュ使用）")
        else:
            print("❌ アイコンファイルが見つかりません")
        
        # 軽量なスタイル設定（必要最小限）
        self.setStyleSheet("""
            QMainWindow { background-color: #f5f5f5; }
            QGroupBox { 
                font-weight: bold; border: 2px solid #cccccc; 
                border-radius: 10px; margin-top: 1ex; padding-top: 10px; 
            }
            QLineEdit { 
                padding: 8px; border: 1px solid #ddd; 
                border-radius: 4px; font-size: 14px; 
            }
            QLineEdit:focus { border-color: #4CAF50; }
            QProgressBar { 
                border: 2px solid #cccccc; border-radius: 5px; text-align: center; 
            }
            QProgressBar::chunk { background-color: #4CAF50; border-radius: 3px; }
        """)
        
        # メインウィジェット
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # メインレイアウト
        main_layout = QVBoxLayout(main_widget)
        
        # メニューバー
        self.create_menu_bar()
        
        # タブウィジェット
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 検索タブ
        self.create_search_tab()
                
        # 結果タブ
        self.create_results_tab()

        # 設定タブ
        self.create_settings_tab()
        
        # ステータスバー
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("準備完了")
        
    def create_menu_bar(self):
        """メニューバーの作成"""
        menubar = self.menuBar()
        
        # ファイルメニュー
        file_menu = menubar.addMenu('ファイル')
        
        # キーワードファイル読み込み
        load_action = QAction('キーワードファイル読み込み', self)
        load_action.triggered.connect(self.load_keywords_file)
        file_menu.addAction(load_action)
        
        # 結果保存
        save_action = QAction('結果を保存', self)
        save_action.triggered.connect(self.save_results)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        # 終了
        exit_action = QAction('終了', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # ヘルプメニュー
        help_menu = menubar.addMenu('ヘルプ')
        
        about_action = QAction('このアプリについて', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_search_tab(self):
        """検索タブの作成"""
        search_widget = QWidget()
        layout = QVBoxLayout(search_widget)
        
        # キーワード入力グループ
        keyword_group = QGroupBox("キーワード入力")
        keyword_layout = QVBoxLayout(keyword_group)
        
        # 単一キーワード入力
        single_layout = QHBoxLayout()
        single_layout.addWidget(QLabel("キーワード:"))
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("検索キーワードを入力してください")
        single_layout.addWidget(self.keyword_input)
        
        self.add_keyword_btn = QPushButton("追加")
        self.add_keyword_btn.clicked.connect(self.add_keyword)
        single_layout.addWidget(self.add_keyword_btn)
        
        keyword_layout.addLayout(single_layout)
        
        # キーワードリスト
        self.keywords_text = QTextEdit()
        self.keywords_text.setMaximumHeight(150)
        self.keywords_text.setPlaceholderText("追加されたキーワードがここに表示されます（1行に1つ）")
        keyword_layout.addWidget(QLabel("キーワードリスト:"))
        keyword_layout.addWidget(self.keywords_text)
        
        # ボタン群
        button_layout = QHBoxLayout()
        
        self.load_file_btn = QPushButton("ファイルから読み込み")
        self.load_file_btn.clicked.connect(self.load_keywords_file)
        button_layout.addWidget(self.load_file_btn)
        
        self.clear_btn = QPushButton("クリア")
        self.clear_btn.clicked.connect(self.clear_keywords)
        button_layout.addWidget(self.clear_btn)
        
        button_layout.addStretch()
        
        keyword_layout.addLayout(button_layout)
        layout.addWidget(keyword_group)
        
        # 検索制御グループ
        control_group = QGroupBox("検索制御")
        control_layout = QHBoxLayout(control_group)
        
        # 検索間隔
        control_layout.addWidget(QLabel("検索間隔(秒):"))
        self.delay_spinbox = QDoubleSpinBox()
        self.delay_spinbox.setRange(0.1, 10.0)
        self.delay_spinbox.setValue(1.0)
        self.delay_spinbox.setSingleStep(0.1)
        control_layout.addWidget(self.delay_spinbox)
        
        control_layout.addStretch()
        
        # 検索ボタン
        self.search_btn = QPushButton("検索開始")
        self.search_btn.clicked.connect(self.start_search)
        self.search_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }")
        control_layout.addWidget(self.search_btn)
        
        self.stop_btn = QPushButton("検索停止")
        self.stop_btn.clicked.connect(self.stop_search)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 10px; }")
        control_layout.addWidget(self.stop_btn)
        
        layout.addWidget(control_group)
          # 検索パラメータグループ
        params_group = QGroupBox("検索パラメータ")
        params_layout = QVBoxLayout(params_group)
        
        # 上段のパラメータ
        params_row1 = QHBoxLayout()
          # 言語制限 (lr)
        params_row1.addWidget(QLabel("言語制限 (lr):"))
        self.lr_combo = QComboBox()
        self.lr_combo.addItems([
            "lang_ja (日本語)",
            "lang_en (英語)",
            "lang_zh (中国語)",
            "lang_ko (韓国語)",
            "lang_fr (フランス語)",
            "lang_de (ドイツ語)",
            "lang_es (スペイン語)",
            "lang_it (イタリア語)",
            "lang_pt (ポルトガル語)",
            "lang_ru (ロシア語)",
            "制限なし"
        ])
        self.lr_combo.setCurrentText("lang_ja (日本語)")
        self.lr_combo.setToolTip("検索結果の言語を制限します")
        params_row1.addWidget(self.lr_combo)
        
        # セーフサーチ (safe)
        params_row1.addWidget(QLabel("セーフサーチ (safe):"))
        self.safe_combo = QComboBox()
        self.safe_combo.addItems([
            "off (無効)",
            "medium (中程度)",
            "high (厳格)"
        ])
        self.safe_combo.setCurrentText("off (無効)")
        self.safe_combo.setToolTip("セーフサーチフィルターの設定")
        params_row1.addWidget(self.safe_combo)
        
        params_row1.addStretch()
        params_layout.addLayout(params_row1)
        
        # 下段のパラメータ
        params_row2 = QHBoxLayout()
        
        # 地域制限 (gl)
        params_row2.addWidget(QLabel("地域制限 (gl):"))
        self.gl_combo = QComboBox()
        self.gl_combo.addItems([
            "jp (日本)",
            "us (アメリカ)",
            "uk (イギリス)",
            "ca (カナダ)",
            "au (オーストラリア)",
            "de (ドイツ)",
            "fr (フランス)",
            "cn (中国)",
            "kr (韓国)",
            "in (インド)",
            "制限なし"
        ])
        self.gl_combo.setCurrentText("jp (日本)")
        self.gl_combo.setToolTip("検索結果の地域を制限します")
        params_row2.addWidget(self.gl_combo)
        
        # インターフェース言語 (hl)
        params_row2.addWidget(QLabel("インターフェース言語 (hl):"))
        self.hl_combo = QComboBox()
        self.hl_combo.addItems([
            "ja (日本語)",
            "en (English)",
            "zh (中文)",
            "ko (한국어)",
            "fr (Français)",
            "de (Deutsch)",
            "es (Español)",
            "it (Italiano)",
            "pt (Português)",            "ru (Русский)"
        ])
        self.hl_combo.setCurrentText("ja (日本語)")
        self.hl_combo.setToolTip("検索インターフェースの言語")
        params_row2.addWidget(self.hl_combo)
        
        params_row2.addStretch()
        params_layout.addLayout(params_row2)
        
        # 3段目のパラメータ（期間制限）
        params_row3 = QHBoxLayout()
        
        # 期間制限 (dateRestrict)        
        params_row3.addWidget(QLabel("期間制限 (dateRestrict):"))
        self.date_restrict_combo = QComboBox()
        self.date_restrict_combo.addItems([
            "制限なし",
            "過去1日",
            "過去1週間",
            "過去1ヶ月",
            "過去3ヶ月",
            "過去6ヶ月",
            "過去1年",
            "過去2年",
            "過去5年",
            "過去10年"
        ])
        self.date_restrict_combo.setCurrentText("制限なし")
        self.date_restrict_combo.setToolTip("検索結果の期間を制限します")
        params_row3.addWidget(self.date_restrict_combo)
        
        params_row3.addStretch()
        params_layout.addLayout(params_row3)
        
        params_layout.addStretch()
        
        layout.addWidget(params_group)
        
        # 進捗表示
        progress_group = QGroupBox("進捗")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("待機中")
        progress_layout.addWidget(self.progress_label)
        
        layout.addWidget(progress_group)
        
        # ログ表示
        log_group = QGroupBox("実行ログ")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        self.tab_widget.addTab(search_widget, "検索")
        
        # Enterキーでキーワード追加
        self.keyword_input.returnPressed.connect(self.add_keyword)
        
    def create_settings_tab(self):
        """設定タブの作成"""
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)
        
        # API設定グループ
        api_group = QGroupBox("API設定")
        api_layout = QVBoxLayout(api_group)
        
        # Google API Key
        api_key_layout = QHBoxLayout()
        api_key_layout.addWidget(QLabel("Google API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Google Custom Search API キーを入力")
        api_key_layout.addWidget(self.api_key_input)
        api_layout.addLayout(api_key_layout)
        
        # Search Engine ID
        engine_id_layout = QHBoxLayout()
        engine_id_layout.addWidget(QLabel("Search Engine ID:"))
        self.engine_id_input = QLineEdit()
        self.engine_id_input.setPlaceholderText("カスタム検索エンジンIDを入力")
        engine_id_layout.addWidget(self.engine_id_input)
        api_layout.addLayout(engine_id_layout)
        
        layout.addWidget(api_group)
        
        # 出力設定グループ
        output_group = QGroupBox("出力設定")
        output_layout = QVBoxLayout(output_group)
        
        # 出力ディレクトリ
        output_dir_layout = QHBoxLayout()
        output_dir_layout.addWidget(QLabel("出力ディレクトリ:"))
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setText("output")
        output_dir_layout.addWidget(self.output_dir_input)
        
        self.browse_btn = QPushButton("参照")
        self.browse_btn.clicked.connect(self.browse_output_dir)
        output_dir_layout.addWidget(self.browse_btn)
        output_layout.addLayout(output_dir_layout)
        
        # ファイル名プレフィックス
        prefix_layout = QHBoxLayout()
        prefix_layout.addWidget(QLabel("ファイル名プレフィックス:"))
        self.prefix_input = QLineEdit()
        self.prefix_input.setText("search_results")
        prefix_layout.addWidget(self.prefix_input)
        output_layout.addLayout(prefix_layout)
        
        layout.addWidget(output_group)
        
        # 検索設定グループ
        search_group = QGroupBox("検索設定")
        search_layout = QHBoxLayout(search_group)
        
        # リトライ回数
        search_layout.addWidget(QLabel("リトライ回数:"))
        self.retry_spinbox = QSpinBox()
        self.retry_spinbox.setRange(0, 10)
        self.retry_spinbox.setValue(3)
        search_layout.addWidget(self.retry_spinbox)
        
        # タイムアウト
        search_layout.addWidget(QLabel("タイムアウト(秒):"))
        self.timeout_spinbox = QSpinBox()
        self.timeout_spinbox.setRange(1, 300)
        self.timeout_spinbox.setValue(10)
        search_layout.addWidget(self.timeout_spinbox)
        
        # 検索結果取得件数
        search_layout.addWidget(QLabel("検索結果取得件数:"))
        self.num_results_spinbox = QSpinBox()
        self.num_results_spinbox.setRange(1, 10)
        self.num_results_spinbox.setValue(1)
        self.num_results_spinbox.setToolTip("1回の検索で取得する結果数（1-10件）")
        search_layout.addWidget(self.num_results_spinbox)
        
        search_layout.addStretch()
        
        layout.addWidget(search_group)
        
        # 設定保存ボタン
        save_config_btn = QPushButton("設定を保存")
        save_config_btn.clicked.connect(self.save_config)
        save_config_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 10px; }")
        layout.addWidget(save_config_btn)
        
        # 接続テストボタン
        test_connection_btn = QPushButton("API接続テスト")
        test_connection_btn.clicked.connect(self.test_api_connection)
        test_connection_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-weight: bold; padding: 10px; }")
        layout.addWidget(test_connection_btn)
        
        layout.addStretch()
        
        self.tab_widget.addTab(settings_widget, "設定")
        
    def create_results_tab(self):
        """結果タブの作成"""
        results_widget = QWidget()
        layout = QVBoxLayout(results_widget)
        
        # 結果統計
        stats_layout = QHBoxLayout()
        self.total_results_label = QLabel("総結果数: 0")
        stats_layout.addWidget(self.total_results_label)
        stats_layout.addStretch()
        
        # 結果クリアボタン
        clear_results_btn = QPushButton("結果をクリア")
        clear_results_btn.clicked.connect(self.clear_results)
        stats_layout.addWidget(clear_results_btn)
        
        layout.addLayout(stats_layout)
          # 結果テーブル
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "キーワード", "順位", "タイトル", "URL", "スニペット", "検索時刻"
        ])
          # テーブルの列幅を調整
        header = self.results_table.horizontalHeader()
        header.setStretchLastSection(False)
        self.results_table.setColumnWidth(0, 150)  # キーワード
        self.results_table.setColumnWidth(1, 60)   # 順位
        self.results_table.setColumnWidth(2, 250)  # タイトル
        self.results_table.setColumnWidth(3, 300)  # URL
        self.results_table.setColumnWidth(4, 350)  # スニペット
        self.results_table.setColumnWidth(5, 150)  # 時刻
        
        layout.addWidget(self.results_table)
        
        # 保存ボタン
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        
        save_csv_btn = QPushButton("CSV形式で保存")
        save_csv_btn.clicked.connect(self.save_results)
        save_csv_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-weight: bold; padding: 10px; }")
        save_layout.addWidget(save_csv_btn)
        
        layout.addLayout(save_layout)
        
        self.tab_widget.addTab(results_widget, "結果")
        
    def add_keyword(self):
        """キーワードを追加"""
        keyword = self.keyword_input.text().strip()
        if keyword:
            # 現在のテキストを取得
            current_text = self.keywords_text.toPlainText()
            keywords = [k.strip() for k in current_text.split('\n') if k.strip()]
              # 重複チェック
            if keyword not in keywords:
                keywords.append(keyword)
                self.keywords_text.setPlainText('\n'.join(keywords))
                self.keyword_input.clear()
                self.log_message(f"キーワードを追加: {keyword}")
            else:
                QMessageBox.warning(self, "警告", "そのキーワードは既に追加されています。")
        
    def clear_keywords(self):
        """キーワードをクリア"""
        self.keywords_text.clear()
        self.keyword_input.clear()
        self.log_message("キーワードリストをクリアしました")
        
    def load_keywords_file(self):
        """キーワードファイルを読み込み（ストリーミング処理で最適化）"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "キーワードファイルを選択", "", "テキストファイル (*.txt);;すべてのファイル (*)"
        )
        
        if file_path:
            try:
                # ファイルサイズを確認
                file_size = os.path.getsize(file_path)
                self.log_message(f"ファイル読み込み開始: {os.path.basename(file_path)} ({file_size:,} bytes)")
                
                keywords = []
                
                # 大きなファイルはストリーミング処理、小さなファイルは一括処理
                if file_size > 1024 * 1024:  # 1MB以上の場合
                    self.log_message("大きなファイルです。ストリーミング処理を開始...")
                    
                    # バッファサイズを最適化（64KB）
                    buffer_size = 64 * 1024
                    
                    with open(file_path, 'r', encoding='utf-8', buffering=buffer_size) as f:
                        for line_number, line in enumerate(f, 1):
                            keyword = line.strip()
                            if keyword:
                                keywords.append(keyword)
                            
                            # 進捗表示（10000行ごと）
                            if line_number % 10000 == 0:
                                self.log_message(f"読み込み進捗: {line_number:,} 行処理済み")
                else:
                    # 小さなファイルは従来通り一括処理
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    keywords = [k.strip() for k in content.split('\n') if k.strip()]
                
                self.keywords_text.setPlainText('\n'.join(keywords))
                self.log_message(f"ファイルから {len(keywords):,} 個のキーワードを読み込みました: {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"ファイル読み込みエラー: {str(e)}")
                self.log_message(f"ファイル読み込みエラー: {str(e)}")
                
    def browse_output_dir(self):
        """出力ディレクトリを選択"""
        dir_path = QFileDialog.getExistingDirectory(self, "出力ディレクトリを選択")
        if dir_path:
            self.output_dir_input.setText(dir_path)
            
    def start_search(self):
        """検索開始"""
        # キーワード取得
        keywords_text = self.keywords_text.toPlainText().strip()
        if not keywords_text:
            QMessageBox.warning(self, "警告", "検索キーワードを入力してください。")
            return
            
        keywords = [k.strip() for k in keywords_text.split('\n') if k.strip()]
        if not keywords:
            QMessageBox.warning(self, "警告", "有効なキーワードが見つかりません。")
            return
            
        # UI状態更新
        self.search_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("検索準備中...")        # ワーカースレッド開始
        num_results = self.num_results_spinbox.value()
        
        # 検索パラメータを取得
        search_params = {}
        
        # lr (言語制限)
        lr_text = self.lr_combo.currentText()
        if lr_text != "制限なし":
            search_params['lr'] = lr_text.split(" ")[0]
        
        # safe (セーフサーチ)
        safe_text = self.safe_combo.currentText()
        search_params['safe'] = safe_text.split(" ")[0]
        
        # gl (地域制限)
        gl_text = self.gl_combo.currentText()
        if gl_text != "制限なし":
            search_params['gl'] = gl_text.split(" ")[0]
          # hl (インターフェース言語)
        hl_text = self.hl_combo.currentText()
        search_params['hl'] = hl_text.split(" ")[0]
          # dateRestrict (期間制限)
        date_restrict_text = self.date_restrict_combo.currentText()
        if date_restrict_text != "制限なし":
            # 表示テキストをAPIパラメータ値にマッピング
            date_restrict_mapping = {
                "過去1日": "d1",
                "過去1週間": "w1",
                "過去1ヶ月": "m1",
                "過去3ヶ月": "m3",
                "過去6ヶ月": "m6",
                "過去1年": "y1",
                "過去2年": "y2",
                "過去5年": "y5",
                "過去10年": "y10"
            }
            search_params['dateRestrict'] = date_restrict_mapping.get(date_restrict_text, "")
        
        self.search_worker = SearchWorker(keywords, self.delay_spinbox.value(), num_results, search_params)
        self.search_worker.progress_updated.connect(self.update_progress)
        self.search_worker.result_found.connect(self.add_result)
        self.search_worker.search_completed.connect(self.search_finished)
        self.search_worker.error_occurred.connect(self.show_error)
        self.search_worker.start()
        
        self.log_message(f"検索開始: {len(keywords)} 個のキーワード")
        
    def stop_search(self):
        """検索停止"""
        if self.search_worker:
            self.search_worker.stop()
            self.search_worker.wait()
            
        self.search_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_label.setText("検索が停止されました")
        self.log_message("検索が停止されました")
        
    def update_progress(self, progress: int, message: str):
        """進捗更新"""
        self.progress_bar.setValue(progress)
        self.progress_label.setText(message)
        
    def add_result(self, result: dict):
        """結果を追加"""
        self.search_results.append(result)
          # テーブルに追加
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        self.results_table.setItem(row, 0, QTableWidgetItem(result['keyword']))
        self.results_table.setItem(row, 1, QTableWidgetItem(str(result.get('rank', 1))))
        self.results_table.setItem(row, 2, QTableWidgetItem(result['title']))
        self.results_table.setItem(row, 3, QTableWidgetItem(result['url']))
        self.results_table.setItem(row, 4, QTableWidgetItem(result['snippet']))
        self.results_table.setItem(row, 5, QTableWidgetItem(result['timestamp']))
        
        # 統計更新
        self.total_results_label.setText(f"総結果数: {len(self.search_results)}")
        
        self.log_message(f"結果取得: {result['keyword']} -> {result['title']}")
        
    def search_finished(self, results: List[dict]):
        """検索完了"""
        self.search_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        self.log_message(f"検索完了: {len(results)} 件の結果")
        
        # 結果タブに切り替え
        self.tab_widget.setCurrentIndex(1)
        
        if results:
            QMessageBox.information(
                self, "検索完了", 
                f"検索が完了しました。\n取得件数: {len(results)} 件"
            )
        else:
            QMessageBox.warning(self, "検索完了", "検索結果が見つかりませんでした。")
            
    def show_error(self, error_message: str):
        """エラー表示"""
        self.log_message(f"エラー: {error_message}")
        QMessageBox.critical(self, "エラー", error_message)
        
        # 検索停止
        self.stop_search()
        
    def clear_results(self):
        """結果をクリア"""
        self.search_results.clear()
        self.results_table.setRowCount(0)
        self.total_results_label.setText("総結果数: 0")
        self.log_message("検索結果をクリアしました")
        
    def save_results(self):
        """結果を保存（ストリーミング処理で最適化）"""
        if not self.search_results:
            QMessageBox.warning(self, "警告", "保存する結果がありません。")
            return
            
        # ファイル名を生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"{self.prefix_input.text()}_{timestamp}.csv"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "結果を保存", default_filename, "CSV ファイル (*.csv);;すべてのファイル (*)"
        )
        
        if file_path:
            try:
                # 大量データの場合はストリーミング処理を使用
                if len(self.search_results) > 1000:
                    self.log_message(f"大量データです。ストリーミング処理で保存中... ({len(self.search_results):,} 件)")
                    self._save_results_streaming(file_path)
                else:
                    # 小さなデータは従来通り
                    self._save_results_standard(file_path)
                
                QMessageBox.information(self, "保存完了", f"結果を保存しました:\n{file_path}")
                self.log_message(f"結果を保存: {file_path}")
                    
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"保存エラー: {str(e)}")
                self.log_message(f"保存エラー: {str(e)}")
    
    def _save_results_standard(self, file_path: str):
        """標準的なCSV保存処理"""
        import csv
        
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ['keyword', 'rank', 'title', 'url', 'snippet', 'timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # ヘッダー行を書き込み
            writer.writeheader()
            
            # データ行を書き込み
            for result in self.search_results:
                writer.writerow(result)
    
    def _save_results_streaming(self, file_path: str):
        """ストリーミングCSV保存処理（大量データ対応）"""
        import csv
        
        # バッファサイズを最適化（64KB）
        buffer_size = 64 * 1024
        batch_size = 1000  # バッチサイズ
        
        with open(file_path, 'w', newline='', encoding='utf-8-sig', buffering=buffer_size) as csvfile:
            fieldnames = ['keyword', 'rank', 'title', 'url', 'snippet', 'timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # ヘッダー行を書き込み
            writer.writeheader()
            
            # バッチ処理でデータを書き込み
            batch = []
            for i, result in enumerate(self.search_results):
                batch.append(result)
                
                # バッチサイズに達したら書き込み
                if len(batch) >= batch_size:
                    writer.writerows(batch)
                    csvfile.flush()  # バッファを強制的にフラッシュ
                    batch = []
                    
                    # 進捗ログ（10000行ごと）
                    if (i + 1) % 10000 == 0:
                        self.log_message(f"保存進捗: {i + 1:,} / {len(self.search_results):,} 行")
              # 残りのバッチを書き込み
            if batch:
                writer.writerows(batch)
                csvfile.flush()
                
    def load_config(self):
        """設定を読み込み（キャッシュ最適化済み）"""
        try:
            # キャッシュ機能付きで設定を読み込み
            from config_manager import get_cached_config
            self.config_manager = get_cached_config(None, skip_validation=True)
            config = self.config_manager.config_data
            
            # API設定
            google_config = config.get('google_api', {})
            self.api_key_input.setText(google_config.get('api_key', ''))
            # search_engine_id と custom_search_engine_id の両方に対応
            engine_id = google_config.get('search_engine_id') or google_config.get('custom_search_engine_id', '')
            self.engine_id_input.setText(engine_id)
            
            # 出力設定
            output_config = config.get('output', {})
            self.output_dir_input.setText(output_config.get('directory', 'output'))
            self.prefix_input.setText(output_config.get('filename_prefix', 'search_results'))
            
            # 検索設定
            search_config = config.get('search', {})
            self.retry_spinbox.setValue(search_config.get('retry_count', 3))
            self.timeout_spinbox.setValue(search_config.get('timeout', 10))
            self.num_results_spinbox.setValue(search_config.get('num', 1))
            
            # 検索パラメータ設定
            # lr (言語制限)
            lr_value = search_config.get('lr', 'lang_ja')
            lr_items = [
                ("lang_ja", "lang_ja (日本語)"),
                ("lang_en", "lang_en (英語)"), 
                ("lang_zh", "lang_zh (中国語)"),
                ("lang_ko", "lang_ko (韓国語)"),
                ("lang_fr", "lang_fr (フランス語)"),
                ("lang_de", "lang_de (ドイツ語)"),
                ("lang_es", "lang_es (スペイン語)"),
                ("lang_it", "lang_it (イタリア語)"),
                ("lang_pt", "lang_pt (ポルトガル語)"),
                ("lang_ru", "lang_ru (ロシア語)"),
                ("", "制限なし")
            ]
            for code, display in lr_items:
                if lr_value == code:
                    self.lr_combo.setCurrentText(display)
                    break
            
            # safe (セーフサーチ)
            safe_value = search_config.get('safe', 'off')
            safe_items = [
                ("off", "off (無効)"),
                ("medium", "medium (中程度)"),
                ("high", "high (厳格)")
            ]
            for code, display in safe_items:
                if safe_value == code:
                    self.safe_combo.setCurrentText(display)
                    break
            
            # gl (地域制限)
            gl_value = search_config.get('gl', 'jp')
            gl_items = [
                ("jp", "jp (日本)"),
                ("us", "us (アメリカ)"),
                ("uk", "uk (イギリス)"),
                ("ca", "ca (カナダ)"),
                ("au", "au (オーストラリア)"),
                ("de", "de (ドイツ)"),
                ("fr", "fr (フランス)"),
                ("cn", "cn (中国)"),
                ("kr", "kr (韓国)"),
                ("in", "in (インド)"),
                ("", "制限なし")
            ]
            for code, display in gl_items:
                if gl_value == code:
                    self.gl_combo.setCurrentText(display)
                    break
              # hl (インターフェース言語)
            hl_value = search_config.get('hl', 'ja')
            hl_items = [
                ("ja", "ja (日本語)"),
                ("en", "en (English)"),
                ("zh", "zh (中文)"),
                ("ko", "ko (한국어)"),
                ("fr", "fr (Français)"),
                ("de", "de (Deutsch)"),
                ("es", "es (Español)"),
                ("it", "it (Italiano)"),
                ("pt", "pt (Português)"),
                ("ru", "ru (Русский)")
            ]
            for code, display in hl_items:
                if hl_value == code:
                    self.hl_combo.setCurrentText(display)
                    break
              # dateRestrict (期間制限)
            date_restrict_value = search_config.get('dateRestrict', '')
            date_restrict_items = [
                ("", "制限なし"),
                ("d1", "過去1日"),
                ("w1", "過去1週間"),
                ("m1", "過去1ヶ月"),
                ("m3", "過去3ヶ月"),
                ("m6", "過去6ヶ月"),
                ("y1", "過去1年"),
                ("y2", "過去2年"),
                ("y5", "過去5年"),
                ("y10", "過去10年")
            ]
            for code, display in date_restrict_items:
                if date_restrict_value == code:
                    self.date_restrict_combo.setCurrentText(display)
                    break
            
            self.log_message("設定を読み込みました")
            
        except Exception as e:
            self.log_message(f"設定読み込みエラー: {str(e)}")            # デフォルト値を設定
            self.output_dir_input.setText('output')
            self.prefix_input.setText('search_results')
            self.retry_spinbox.setValue(3)
            self.timeout_spinbox.setValue(10)
            self.num_results_spinbox.setValue(1)
            
    def test_api_connection(self):
        """API接続をテスト"""
        # 現在の設定を一時保存
        self.save_config()
        
        try:
            # SearchToolで接続テスト（GUI用初期化）
            search_tool = SearchTool()
            if search_tool.initialize_for_gui():
                if search_tool.test_connection():
                    QMessageBox.information(self, "接続テスト", "✅ API接続テストに成功しました！")
                    self.log_message("API接続テスト: 成功")
                else:
                    QMessageBox.warning(self, "接続テスト", "❌ API接続テストに失敗しました。\n\nAPI キーまたは検索エンジンIDを確認してください。")
                    self.log_message("API接続テスト: 失敗")
            else:
                QMessageBox.critical(self, "接続テスト", "❌ 初期化に失敗しました。設定を確認してください。")
                self.log_message("API接続テスト: 初期化失敗")
        except Exception as e:
            QMessageBox.critical(self, "接続テスト", f"❌ 接続テストでエラーが発生しました:\n{str(e)}")
            self.log_message(f"API接続テストエラー: {str(e)}")
            
    def save_config(self):
        """設定を保存"""
        try:
            if not self.config_manager:
                self.config_manager = ConfigManager(skip_validation=True)
              # ConfigManagerのsetterメソッドを使用して設定を更新
            self.config_manager.set_google_api_key(self.api_key_input.text())
            self.config_manager.set_search_engine_id(self.engine_id_input.text())
            self.config_manager.set_output_directory(self.output_dir_input.text())
            self.config_manager.set_output_filename_prefix(self.prefix_input.text())
            self.config_manager.set_retry_count(self.retry_spinbox.value())
            self.config_manager.set_timeout(self.timeout_spinbox.value())
            self.config_manager.set_search_results_num(self.num_results_spinbox.value())
            
            # 検索パラメータの保存
            # lr (言語制限)
            lr_text = self.lr_combo.currentText()
            if lr_text == "制限なし":
                lr_value = ""
            else:
                lr_value = lr_text.split(" ")[0]
            self.config_manager.set_search_lr(lr_value)
            
            # safe (セーフサーチ)
            safe_text = self.safe_combo.currentText()
            safe_value = safe_text.split(" ")[0]
            self.config_manager.set_search_safe(safe_value)
            
            # gl (地域制限)
            gl_text = self.gl_combo.currentText()
            if gl_text == "制限なし":
                gl_value = ""
            else:
                gl_value = gl_text.split(" ")[0]
            self.config_manager.set_search_gl(gl_value)
              # hl (インターフェース言語)
            hl_text = self.hl_combo.currentText()
            hl_value = hl_text.split(" ")[0]
            self.config_manager.set_search_hl(hl_value)
              # dateRestrict (期間制限)
            date_restrict_text = self.date_restrict_combo.currentText()
            if date_restrict_text == "制限なし":
                date_restrict_value = ""
            else:
                # 表示テキストをAPIパラメータ値にマッピング
                date_restrict_mapping = {
                    "過去1日": "d1",
                    "過去1週間": "w1",
                    "過去1ヶ月": "m1",
                    "過去3ヶ月": "m3",
                    "過去6ヶ月": "m6",
                    "過去1年": "y1",
                    "過去2年": "y2",
                    "過去5年": "y5",
                    "過去10年": "y10"
                }
                date_restrict_value = date_restrict_mapping.get(date_restrict_text, "")
            self.config_manager.set_search_date_restrict(date_restrict_value)
            
            # ConfigManagerの保存メソッドを使用
            if self.config_manager.save_config():
                QMessageBox.information(self, "保存完了", 
                    f"設定を保存しました。\n保存先: {self.config_manager.get_config_file_path()}")
                self.log_message(f"設定を保存しました: {self.config_manager.get_config_file_path()}")
            else:
                QMessageBox.warning(self, "保存失敗", "設定の保存に失敗しました。")
                self.log_message("設定保存に失敗しました")
            
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"設定保存エラー: {str(e)}")
            self.log_message(f"設定保存エラー: {str(e)}")
            
    def log_message(self, message: str):
        """ログメッセージを追加"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        self.log_text.append(log_entry)
        
        # 自動スクロール
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
        
        # ステータスバーにも表示
        self.status_bar.showMessage(message, 3000)
        
    def show_about(self):
        """アプリケーション情報を表示"""
        QMessageBox.about(
            self, "Google Search Tool について",
            """Google Search Tool - PRO
            
バージョン: 1.0.0
            
Google Custom Search API を使用して
キーワード検索を行い、結果をCSV形式で
出力するツールです。

開発: Python + PyQt6"""
        )
        
    def closeEvent(self, event):
        """アプリケーション終了時の処理"""
        if self.search_worker and self.search_worker.isRunning():
            reply = QMessageBox.question(
                self, "確認", 
                "検索が実行中です。終了しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.search_worker.stop()
                self.search_worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """GUIアプリケーションのメイン関数"""
    app = QApplication(sys.argv)
      # アプリケーション情報設定
    app.setApplicationName("Google Search Tool")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Google Search Tool")    # アプリケーションアイコンを設定
    # PyInstallerでのEXE実行時も考慮したパス取得
    icon_path = get_resource_path(os.path.join('icon', 'app_icon.ico'))
    
    print(f"🔍 アプリケーションアイコンパス: {icon_path}")
    print(f"📁 アプリケーションアイコンファイル存在: {os.path.exists(icon_path)}")
    if os.path.exists(icon_path):
        file_size = os.path.getsize(icon_path)
        print(f"📏 アプリケーションアイコンファイルサイズ: {file_size} bytes")
        try:
            icon = QIcon(icon_path)
            app.setWindowIcon(icon)
            print("✅ アプリケーションアイコン設定完了")
        except Exception as e:
            print(f"❌ アプリケーションアイコン設定エラー: {e}")
    else:
        print("❌ アプリケーションアイコンファイルが見つかりません")
    
    # メインウィンドウ作成・表示
    window = GoogleSearchGUI()
    window.show()
    
    # イベントループ開始
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

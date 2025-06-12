#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Virtual Table Widget - 高性能な仮想化テーブル表示ウィジェット
"""

from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QHeaderView,
    QLabel, QPushButton, QLineEdit, QComboBox, QSpinBox,
    QProgressBar, QFrame, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QModelIndex
from PyQt6.QtGui import QFont, QAction

try:
    from .virtual_table_model import FilterableVirtualTableModel
except ImportError:
    from virtual_table_model import FilterableVirtualTableModel


class VirtualTableWidget(QWidget):
    """
    高性能な仮想化テーブル表示ウィジェット
    
    特徴:
    - 大量データの効率的表示
    - リアルタイムフィルタリング
    - ページネーション（オプション）
    - 列ソート
    - カスタマイズ可能なヘッダー
    """
    
    # シグナル
    rowSelected = pyqtSignal(int, dict)  # 行選択時 (行番号, データ)
    dataChanged = pyqtSignal(int)        # データ変更時 (行数)
    filterChanged = pyqtSignal(str, int) # フィルタ変更時 (フィルタテキスト, 結果数)
    
    def __init__(self, enable_pagination: bool = False, page_size: int = 1000, parent=None):
        super().__init__(parent)
        
        self.enable_pagination = enable_pagination
        self.page_size = page_size
        self.current_page = 0
        
        # モデル初期化
        self.model = FilterableVirtualTableModel(self)
        
        # UI初期化
        self._initUI()
        self._connectSignals()
        
        # パフォーマンス最適化
        self._setupOptimizations()
    
    def _initUI(self):
        """UIを初期化"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # ツールバー
        self._createToolbar(layout)
        
        # テーブルビュー
        self._createTableView(layout)
        
        # ページネーションコントロール（有効な場合）
        if self.enable_pagination:
            self._createPaginationControls(layout)
        
        # ステータスバー
        self._createStatusBar(layout)
    
    def _createToolbar(self, layout: QVBoxLayout):
        """ツールバーを作成"""
        toolbar_frame = QFrame()
        toolbar_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        toolbar_frame.setMaximumHeight(50)
        
        toolbar_layout = QHBoxLayout(toolbar_frame)
        
        # 検索/フィルタ
        toolbar_layout.addWidget(QLabel("フィルタ:"))
        
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("検索キーワードを入力...")
        self.filter_input.setMaximumWidth(300)
        toolbar_layout.addWidget(self.filter_input)
        
        # フィルタクリアボタン
        self.clear_filter_btn = QPushButton("クリア")
        self.clear_filter_btn.setMaximumWidth(60)
        toolbar_layout.addWidget(self.clear_filter_btn)
        
        toolbar_layout.addStretch()
        
        # 結果数表示
        self.result_count_label = QLabel("総結果数: 0")
        self.result_count_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        toolbar_layout.addWidget(self.result_count_label)
        
        layout.addWidget(toolbar_frame)
    
    def _createTableView(self, layout: QVBoxLayout):
        """テーブルビューを作成"""
        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        
        # テーブル設定
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table_view.setSortingEnabled(True)
        self.table_view.setShowGrid(True)
        
        # ヘッダー設定
        header = self.table_view.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        # 列幅設定
        self._setupColumnWidths()
        
        # 垂直ヘッダー
        vheader = self.table_view.verticalHeader()
        vheader.setVisible(True)
        vheader.setDefaultSectionSize(30)
        
        layout.addWidget(self.table_view)
    
    def _setupColumnWidths(self):
        """列幅を設定"""
        # デフォルト列幅
        default_widths = [150, 60, 250, 300, 350, 150]  # キーワード, 順位, タイトル, URL, スニペット, 時刻
        
        for i, width in enumerate(default_widths):
            if i < self.model.columnCount():
                self.table_view.setColumnWidth(i, width)
    
    def _createPaginationControls(self, layout: QVBoxLayout):
        """ページネーションコントロールを作成"""
        pagination_frame = QFrame()
        pagination_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        pagination_frame.setMaximumHeight(50)
        
        pagination_layout = QHBoxLayout(pagination_frame)
        
        # 前のページボタン
        self.prev_btn = QPushButton("< 前")
        self.prev_btn.setEnabled(False)
        pagination_layout.addWidget(self.prev_btn)
        
        # ページ情報
        self.page_info_label = QLabel("ページ 1 / 1")
        pagination_layout.addWidget(self.page_info_label)
        
        # 次のページボタン
        self.next_btn = QPushButton("次 >")
        self.next_btn.setEnabled(False)
        pagination_layout.addWidget(self.next_btn)
        
        pagination_layout.addStretch()
        
        # ページサイズ設定
        pagination_layout.addWidget(QLabel("ページサイズ:"))
        self.page_size_spinbox = QSpinBox()
        self.page_size_spinbox.setRange(100, 10000)
        self.page_size_spinbox.setValue(self.page_size)
        self.page_size_spinbox.setSingleStep(100)
        pagination_layout.addWidget(self.page_size_spinbox)
        
        layout.addWidget(pagination_frame)
    
    def _createStatusBar(self, layout: QVBoxLayout):
        """ステータスバーを作成"""
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        status_frame.setMaximumHeight(30)
        
        status_layout = QHBoxLayout(status_frame)
        
        # 選択行情報
        self.selection_label = QLabel("選択なし")
        self.selection_label.setStyleSheet("color: #666;")
        status_layout.addWidget(self.selection_label)
        
        status_layout.addStretch()
        
        # パフォーマンス情報（デバッグ用）
        self.perf_label = QLabel("")
        self.perf_label.setStyleSheet("color: #888; font-size: 11px;")
        status_layout.addWidget(self.perf_label)
        
        layout.addWidget(status_frame)
    
    def _connectSignals(self):
        """シグナルを接続"""
        # フィルタ
        self.filter_input.textChanged.connect(self._onFilterChanged)
        self.clear_filter_btn.clicked.connect(self._onClearFilter)
        
        # テーブル選択
        self.table_view.selectionModel().currentRowChanged.connect(self._onRowSelected)
        
        # ページネーション（有効な場合）
        if self.enable_pagination:
            self.prev_btn.clicked.connect(self._onPrevPage)
            self.next_btn.clicked.connect(self._onNextPage)
            self.page_size_spinbox.valueChanged.connect(self._onPageSizeChanged)
        
        # モデル変更
        self.model.modelReset.connect(self._onModelReset)
        self.model.rowsInserted.connect(self._onRowsInserted)
    
    def _setupOptimizations(self):
        """パフォーマンス最適化を設定"""
        # 遅延フィルタ更新（タイピング中の負荷軽減）
        self.filter_timer = QTimer()
        self.filter_timer.setSingleShot(True)
        self.filter_timer.timeout.connect(self._applyFilter)
        
        # テーブルビューの最適化
        # PyQt6のQTableViewではsetUniformRowHeightsは使用不可
        self.table_view.setUpdatesEnabled(True)
    
    def _onFilterChanged(self, text: str):
        """フィルタテキスト変更時"""
        # 遅延実行でパフォーマンスを改善
        self.filter_timer.stop()
        self.filter_timer.start(300)  # 300ms後に実行
    
    def _applyFilter(self):
        """フィルタを適用"""
        filter_text = self.filter_input.text()
        self.model.setFilter(filter_text)
        
        # 結果数更新
        filtered_count = self.model.getFilteredCount()
        total_count = self.model.getResultCount()
        
        if filter_text:
            self.result_count_label.setText(f"フィルタ結果: {filtered_count:,} / {total_count:,}")
        else:
            self.result_count_label.setText(f"総結果数: {total_count:,}")
        
        # シグナル発信
        self.filterChanged.emit(filter_text, filtered_count)
        
        # ページネーション更新
        if self.enable_pagination:
            self._updatePaginationControls()
    
    def _onClearFilter(self):
        """フィルタクリア"""
        self.filter_input.clear()
        self.model.clearFilter()
        
        # 結果数更新
        total_count = self.model.getResultCount()
        self.result_count_label.setText(f"総結果数: {total_count:,}")
        
        # シグナル発信
        self.filterChanged.emit("", total_count)
    
    def _onRowSelected(self, current: QModelIndex, previous: QModelIndex):
        """行選択時"""
        if current.isValid():
            row = current.row()
            data = self.model.data(current, Qt.ItemDataRole.UserRole)
            
            # 選択行情報更新
            keyword = self.model.data(self.model.index(row, 0), Qt.ItemDataRole.DisplayRole)
            self.selection_label.setText(f"選択: 行 {row + 1} - {keyword}")
            
            # シグナル発信
            result_data = {}
            for col in range(self.model.columnCount()):
                header = self.model.headerData(col, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
                value = self.model.data(self.model.index(row, col), Qt.ItemDataRole.DisplayRole)
                result_data[str(header)] = value
            
            self.rowSelected.emit(row, result_data)
        else:
            self.selection_label.setText("選択なし")
    
    def _onModelReset(self):
        """モデルリセット時"""
        self._updateDisplayInfo()
    
    def _onRowsInserted(self, parent: QModelIndex, start: int, end: int):
        """行追加時"""
        self._updateDisplayInfo()
    
    def _updateDisplayInfo(self):
        """表示情報を更新"""
        total_count = self.model.getResultCount()
        
        if self.model._use_filter:
            filtered_count = self.model.getFilteredCount()
            self.result_count_label.setText(f"フィルタ結果: {filtered_count:,} / {total_count:,}")
        else:
            self.result_count_label.setText(f"総結果数: {total_count:,}")
        
        # シグナル発信
        self.dataChanged.emit(total_count)
        
        # ページネーション更新
        if self.enable_pagination:
            self._updatePaginationControls()
    
    def _onPrevPage(self):
        """前のページ"""
        if self.current_page > 0:
            self.current_page -= 1
            self._updatePage()
    
    def _onNextPage(self):
        """次のページ"""
        max_page = self._getMaxPage()
        if self.current_page < max_page:
            self.current_page += 1
            self._updatePage()
    
    def _onPageSizeChanged(self, value: int):
        """ページサイズ変更"""
        self.page_size = value
        self.current_page = 0  # 最初のページに戻る
        self._updatePage()
    
    def _updatePage(self):
        """ページ表示を更新"""
        # TODO: 実際のページネーション実装
        # 現在は表示のみ
        self._updatePaginationControls()
    
    def _updatePaginationControls(self):
        """ページネーションコントロールを更新"""
        if not self.enable_pagination:
            return
        
        max_page = self._getMaxPage()
        
        # ボタン状態
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled(self.current_page < max_page)
        
        # ページ情報
        self.page_info_label.setText(f"ページ {self.current_page + 1} / {max_page + 1}")
    
    def _getMaxPage(self) -> int:
        """最大ページ数を取得"""
        row_count = self.model.rowCount()
        if row_count == 0:
            return 0
        return (row_count - 1) // self.page_size
    
    # パブリックメソッド
    
    def setData(self, results: List[Dict[str, Any]]):
        """データを設定"""
        self.model.setData(results)
        self._updateDisplayInfo()
        
        # パフォーマンス情報更新
        self.perf_label.setText(f"表示: {len(results):,} 件")
    
    def addResult(self, result: Dict[str, Any]):
        """1件の結果を追加"""
        self.model.addResult(result)
    
    def addResults(self, results: List[Dict[str, Any]]):
        """複数の結果を追加"""
        if results:
            self.model.addResults(results)
            
            # パフォーマンス情報更新
            total = self.model.getResultCount()
            self.perf_label.setText(f"表示: {total:,} 件")
    
    def clearData(self):
        """データをクリア"""
        self.model.clearData()
        self.selection_label.setText("選択なし")
        self.perf_label.setText("")
    
    def getData(self) -> List[Dict[str, Any]]:
        """全データを取得"""
        return self.model.getData()
    
    def getSelectedResult(self) -> Optional[Dict[str, Any]]:
        """選択された結果を取得"""
        selection = self.table_view.selectionModel().currentIndex()
        if selection.isValid():
            row = selection.row()
            return self.model.getResult(row)
        return None
    
    def getResultCount(self) -> int:
        """結果数を取得"""
        return self.model.getResultCount()
    
    def getFilteredCount(self) -> int:
        """フィルタ後の結果数を取得"""
        return self.model.getFilteredCount()
    
    def setFilter(self, filter_text: str):
        """フィルタを設定"""
        self.filter_input.setText(filter_text)
        self.model.setFilter(filter_text)
        self._updateDisplayInfo()
    
    def clearFilter(self):
        """フィルタをクリア"""
        self._onClearFilter()
    
    def selectRow(self, row: int):
        """指定行を選択"""
        if 0 <= row < self.model.rowCount():
            index = self.model.index(row, 0)
            self.table_view.selectionModel().setCurrentIndex(
                index, self.table_view.selectionModel().SelectionFlag.ClearAndSelect | 
                self.table_view.selectionModel().SelectionFlag.Rows
            )
            self.table_view.scrollTo(index)
    
    def exportData(self) -> List[Dict[str, Any]]:
        """エクスポート用データを取得（フィルタ適用済み）"""
        if self.model._use_filter:
            return self.model._filtered_data.copy()
        return self.model.getData()

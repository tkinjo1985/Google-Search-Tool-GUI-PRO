#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Virtual Table Model - 大量データ表示用の仮想化テーブルモデル
"""

from typing import Any, List, Dict, Optional
from PyQt6.QtCore import QAbstractTableModel, Qt, QVariant, QModelIndex
from PyQt6.QtGui import QFont


class VirtualTableModel(QAbstractTableModel):
    """
    検索結果表示用の仮想化テーブルモデル
    
    大量データを効率的に表示するために、必要な行のみを描画する
    仮想化アプローチを採用
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []
        self._headers = ["キーワード", "順位", "タイトル", "URL", "スニペット", "検索時刻"]
        self._column_keys = ["keyword", "rank", "title", "url", "snippet", "timestamp"]
        
        # キャッシュサイズ（表示する行数を制限）
        self._cache_size = 1000
        self._visible_start = 0
        self._visible_end = 0
    
    def rowCount(self, parent=QModelIndex()) -> int:
        """行数を返す"""
        if parent.isValid():
            return 0
        return len(self._data)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        """列数を返す"""
        if parent.isValid():
            return 0
        return len(self._headers)
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> QVariant:
        """セルデータを返す"""
        if not index.isValid():
            return QVariant()
        
        row = index.row()
        col = index.column()
        
        if row < 0 or row >= len(self._data) or col < 0 or col >= len(self._column_keys):
            return QVariant()
        
        item = self._data[row]
        column_key = self._column_keys[col]
        
        if role == Qt.ItemDataRole.DisplayRole:
            value = item.get(column_key, "")
            
            # 長いテキストを切り詰め
            if column_key in ["title", "snippet"] and len(str(value)) > 100:
                return str(value)[:97] + "..."
            elif column_key == "url" and len(str(value)) > 80:
                return str(value)[:77] + "..."
            
            return str(value)
        
        elif role == Qt.ItemDataRole.ToolTipRole:
            # ツールチップで完全なテキストを表示
            value = item.get(column_key, "")
            return str(value)
        
        elif role == Qt.ItemDataRole.FontRole:
            # URL列はモノスペースフォント
            if column_key == "url":
                font = QFont("Consolas, Monaco, monospace")
                font.setPointSize(9)
                return font
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            # 順位列は中央揃え
            if column_key == "rank":
                return Qt.AlignmentFlag.AlignCenter
        
        return QVariant()
    
    def headerData(self, section: int, orientation: Qt.Orientation, 
                   role: int = Qt.ItemDataRole.DisplayRole) -> QVariant:
        """ヘッダーデータを返す"""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        elif orientation == Qt.Orientation.Vertical and role == Qt.ItemDataRole.DisplayRole:
            return str(section + 1)
        
        return QVariant()
    
    def setData(self, results: List[Dict[str, Any]]) -> None:
        """データを設定"""
        self.beginResetModel()
        self._data = results.copy()
        self.endResetModel()
    
    def addResult(self, result: Dict[str, Any]) -> None:
        """1件の結果を追加"""
        row = len(self._data)
        self.beginInsertRows(QModelIndex(), row, row)
        self._data.append(result)
        self.endInsertRows()
    
    def addResults(self, results: List[Dict[str, Any]]) -> None:
        """複数の結果を追加"""
        if not results:
            return
        
        start_row = len(self._data)
        end_row = start_row + len(results) - 1
        
        self.beginInsertRows(QModelIndex(), start_row, end_row)
        self._data.extend(results)
        self.endInsertRows()
    
    def clearData(self) -> None:
        """データをクリア"""
        self.beginResetModel()
        self._data.clear()
        self.endResetModel()
    
    def getData(self) -> List[Dict[str, Any]]:
        """全データを取得"""
        return self._data.copy()
    
    def getResultCount(self) -> int:
        """結果数を取得"""
        return len(self._data)
    
    def getResult(self, row: int) -> Optional[Dict[str, Any]]:
        """指定行の結果を取得"""
        if 0 <= row < len(self._data):
            return self._data[row].copy()
        return None
    
    def updateVisibleRange(self, start: int, end: int) -> None:
        """表示範囲を更新（将来的な最適化用）"""
        self._visible_start = max(0, start)
        self._visible_end = min(len(self._data), end)
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """アイテムフラグを返す"""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
    
    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        """列でソート"""
        if column < 0 or column >= len(self._column_keys):
            return
        
        column_key = self._column_keys[column]
        reverse = (order == Qt.SortOrder.DescendingOrder)
        
        self.layoutAboutToBeChanged.emit()
        
        try:
            if column_key == "rank":
                # 順位は数値でソート
                self._data.sort(key=lambda x: int(x.get(column_key, 0)), reverse=reverse)
            else:
                # その他は文字列でソート
                self._data.sort(key=lambda x: str(x.get(column_key, "")), reverse=reverse)
        except (ValueError, TypeError):
            # ソートエラーが発生した場合は文字列ソートにフォールバック
            self._data.sort(key=lambda x: str(x.get(column_key, "")), reverse=reverse)
        
        self.layoutChanged.emit()


class FilterableVirtualTableModel(VirtualTableModel):
    """
    フィルタリング機能付きの仮想テーブルモデル
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._filtered_data: List[Dict[str, Any]] = []
        self._filter_text = ""
        self._use_filter = False
    
    def rowCount(self, parent=QModelIndex()) -> int:
        """行数を返す（フィルタ適用時は絞り込み後の行数）"""
        if parent.isValid():
            return 0
        return len(self._filtered_data) if self._use_filter else len(self._data)
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> QVariant:
        """セルデータを返す（フィルタ適用時は絞り込み後のデータ）"""
        if not index.isValid():
            return QVariant()
        
        row = index.row()
        col = index.column()
        
        current_data = self._filtered_data if self._use_filter else self._data
        
        if row < 0 or row >= len(current_data) or col < 0 or col >= len(self._column_keys):
            return QVariant()
        
        item = current_data[row]
        column_key = self._column_keys[col]
        
        if role == Qt.ItemDataRole.DisplayRole:
            value = item.get(column_key, "")
            
            # 長いテキストを切り詰め
            if column_key in ["title", "snippet"] and len(str(value)) > 100:
                return str(value)[:97] + "..."
            elif column_key == "url" and len(str(value)) > 80:
                return str(value)[:77] + "..."
            
            return str(value)
        
        elif role == Qt.ItemDataRole.ToolTipRole:
            # ツールチップで完全なテキストを表示
            value = item.get(column_key, "")
            return str(value)
        
        elif role == Qt.ItemDataRole.FontRole:
            # URL列はモノスペースフォント
            if column_key == "url":
                font = QFont("Consolas, Monaco, monospace")
                font.setPointSize(9)
                return font
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            # 順位列は中央揃え
            if column_key == "rank":
                return Qt.AlignmentFlag.AlignCenter
        
        return QVariant()
    
    def setFilter(self, filter_text: str) -> None:
        """フィルタを設定"""
        self._filter_text = filter_text.lower().strip()
        self._use_filter = bool(self._filter_text)
        
        if self._use_filter:
            self._applyFilter()
        else:
            self.beginResetModel()
            self._filtered_data.clear()
            self.endResetModel()
    
    def _applyFilter(self) -> None:
        """フィルタを適用"""
        self.beginResetModel()
        
        self._filtered_data.clear()
        
        for item in self._data:
            # 全ての列でフィルタテキストを検索
            match = False
            for key in self._column_keys:
                value = str(item.get(key, "")).lower()
                if self._filter_text in value:
                    match = True
                    break
            
            if match:
                self._filtered_data.append(item)
        
        self.endResetModel()
    
    def clearFilter(self) -> None:
        """フィルタをクリア"""
        self.setFilter("")
    
    def getFilteredCount(self) -> int:
        """フィルタ後の結果数を取得"""
        return len(self._filtered_data) if self._use_filter else len(self._data)
    
    def setData(self, results: List[Dict[str, Any]]) -> None:
        """データを設定（フィルタも再適用）"""
        super().setData(results)
        if self._use_filter:
            self._applyFilter()
    
    def addResult(self, result: Dict[str, Any]) -> None:
        """1件の結果を追加（フィルタも考慮）"""
        # 元データに追加
        super().addResult(result)
        
        # フィルタが有効な場合は再適用
        if self._use_filter:
            self._applyFilter()
    
    def addResults(self, results: List[Dict[str, Any]]) -> None:
        """複数の結果を追加（フィルタも考慮）"""
        # 元データに追加
        super().addResults(results)
        
        # フィルタが有効な場合は再適用
        if self._use_filter:
            self._applyFilter()

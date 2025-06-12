#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
検索結果データモデル
SearchResultクラスとデータ構造定義、データ検証機能を提供
"""

import re
import html
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class SearchResult:
    """検索結果データクラス"""
    
    title: str = ""
    url: str = ""
    snippet: str = ""
    search_query: str = ""
    rank: int = 1
    search_datetime: datetime = field(default_factory=datetime.now)
    display_link: str = ""
    formatted_url: str = ""
    page_map: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初期化後の処理でデータを正規化"""
        self.title = self._normalize_text(self.title)
        self.snippet = self._normalize_text(self.snippet)
        self.url = self._normalize_url(self.url)
        self.display_link = self._normalize_text(self.display_link)
        self.formatted_url = self._normalize_text(self.formatted_url)
    
    def _normalize_text(self, text: str) -> str:
        """テキストの正規化処理"""
        if not text:
            return ""
        
        # HTMLエンティティをデコード
        text = html.unescape(text)
        
        # HTMLタグを除去
        text = re.sub(r'<[^>]+>', '', text)
        
        # 余分な空白を除去
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 制御文字を除去
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        return text
    
    def _normalize_url(self, url: str) -> str:
        """URLの正規化処理"""
        if not url:
            return ""
        
        # 余分な空白を除去
        url = url.strip()
        
        # URLスキーマが無い場合はhttpを追加
        if url and not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        return url
    
    def is_valid(self) -> bool:
        """データの有効性をチェック"""
        # 必須フィールドの存在確認
        if not self.title and not self.snippet:
            return False
        
        if not self.url:
            return False
        
        # URLの形式チェック
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if not re.match(url_pattern, self.url):
            return False
        
        # ランクの範囲チェック
        if self.rank < 1 or self.rank > 100:
            return False
        
        return True
    
    def get_domain(self) -> str:
        """URLからドメイン名を抽出"""
        import urllib.parse
        try:
            parsed = urllib.parse.urlparse(self.url)
            return parsed.netloc.lower()
        except:
            return ""
    
    def get_short_snippet(self, max_length: int = 100) -> str:
        """短縮されたスニペットを取得"""
        if len(self.snippet) <= max_length:
            return self.snippet
        
        # 単語境界で切り詰める
        truncated = self.snippet[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:  # 80%以上の位置に空白がある場合
            truncated = truncated[:last_space]
        
        return truncated + "..."
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'title': self.title,
            'url': self.url,
            'snippet': self.snippet,
            'search_query': self.search_query,
            'rank': self.rank,
            'search_datetime': self.search_datetime.isoformat(),
            'display_link': self.display_link,
            'formatted_url': self.formatted_url,
            'domain': self.get_domain(),
            'short_snippet': self.get_short_snippet()
        }
    
    def to_csv_row(self) -> list:
        """CSV行データに変換"""
        return [
            self.search_query,
            str(self.rank),
            self.title,
            self.url,
            self.snippet,
            self.search_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            self.get_domain()
        ]
    
    @staticmethod
    def get_csv_headers() -> list:
        """CSVヘッダーを取得"""
        return [
            '検索キーワード',
            '順位',
            'タイトル',
            'URL',
            'スニペット',
            '検索日時',
            'ドメイン'
        ]
    
    @classmethod
    def from_google_api_response(cls, item: Dict[str, Any], query: str, rank: int = 1) -> 'SearchResult':
        """
        Google APIレスポンスからSearchResultオブジェクトを作成
        
        Args:
            item: Google APIのitemオブジェクト
            query: 検索クエリ
            rank: 検索順位
            
        Returns:
            SearchResultオブジェクト
        """
        return cls(
            title=item.get('title', ''),
            url=item.get('link', ''),
            snippet=item.get('snippet', ''),
            search_query=query,
            rank=rank,
            display_link=item.get('displayLink', ''),
            formatted_url=item.get('formattedUrl', ''),
            page_map=item.get('pagemap', {})
        )
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"SearchResult(query='{self.search_query}', rank={self.rank}, title='{self.title[:50]}...', url='{self.url}')"
    
    def __repr__(self) -> str:
        """開発者向け文字列表現"""
        return self.__str__()


class SearchResultFilter:
    """検索結果フィルタリングクラス"""
    
    def __init__(self):
        # 除外するドメインのパターン
        self.excluded_domains = {
            'ads.google.com',
            'googleadservices.com',
            'doubleclick.net',
            'googletagmanager.com'
        }
        
        # 除外するタイトルパターン
        self.excluded_title_patterns = [
            r'^ads?\s',
            r'^sponsored\s',
            r'^pr\s',
            r'^広告\s'
        ]
    
    def is_valid_result(self, result: SearchResult) -> bool:
        """検索結果が有効かどうかを判定"""
        # 基本的なデータ検証
        if not result.is_valid():
            return False
        
        # ドメインフィルタリング
        domain = result.get_domain()
        if domain in self.excluded_domains:
            return False
        
        # タイトルパターンフィルタリング
        title_lower = result.title.lower()
        for pattern in self.excluded_title_patterns:
            if re.search(pattern, title_lower, re.IGNORECASE):
                return False
        
        return True
    
    def filter_results(self, results: list[SearchResult]) -> list[SearchResult]:
        """検索結果リストをフィルタリング"""
        return [result for result in results if self.is_valid_result(result)]
    
    def remove_duplicates(self, results: list[SearchResult]) -> list[SearchResult]:
        """重複する検索結果を除去"""
        seen_urls = set()
        unique_results = []
        
        for result in results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)
        
        return unique_results


if __name__ == "__main__":
    # テスト実行
    print("SearchResultクラスのテストを実行中...")
    
    # テストデータを作成
    test_item = {
        'title': 'Test <b>Title</b> with HTML',
        'link': 'https://example.com/test',
        'snippet': 'This is a test snippet with\nmultiple lines and   extra spaces.',
        'displayLink': 'example.com',
        'formattedUrl': 'https://example.com/test'
    }
    
    # SearchResultオブジェクトを作成
    result = SearchResult.from_google_api_response(test_item, "test query", 1)
    
    print(f"作成された結果: {result}")
    print(f"有効性チェック: {result.is_valid()}")
    print(f"ドメイン: {result.get_domain()}")
    print(f"短縮スニペット: {result.get_short_snippet(50)}")
    
    # CSV形式のテスト
    print(f"CSVヘッダー: {SearchResult.get_csv_headers()}")
    print(f"CSV行データ: {result.to_csv_row()}")
    
    # フィルタリングのテスト
    filter_obj = SearchResultFilter()
    print(f"フィルタリング結果: {filter_obj.is_valid_result(result)}")
    
    print("SearchResultクラスのテスト完了")

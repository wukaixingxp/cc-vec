"""Text processing pipeline for extracting clean content from WARC records."""

import re
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

try:
    from bs4 import BeautifulSoup, Comment

    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

logger = logging.getLogger(__name__)


class WARCTextProcessor:
    """Process WARC content to extract clean text suitable for RAG applications."""

    def __init__(self):
        """Initialize the processor."""
        if not HAS_BS4:
            logger.warning(
                "BeautifulSoup4 not available. HTML parsing will be limited."
            )

        # Content that should be removed from final text
        self.remove_tags = {
            "script",
            "style",
            "nav",
            "header",
            "footer",
            "aside",
            "noscript",
            "meta",
            "link",
            "iframe",
            "embed",
            "object",
        }

        # Patterns for cleaning text
        self.cleanup_patterns = [
            (r"\s+", " "),  # Multiple whitespace to single space
            (r"\n\s*\n", "\n"),  # Multiple newlines to single
            (r"^\s+|\s+$", ""),  # Leading/trailing whitespace
        ]

    def extract_html_from_warc(self, warc_content: bytes) -> Optional[str]:
        """Extract HTML content from WARC format.

        Args:
            warc_content: Raw WARC record bytes

        Returns:
            HTML content as string, or None if extraction fails
        """
        try:
            # Decode content
            text = warc_content.decode("utf-8", errors="replace")

            # Split on double CRLF to separate headers from content
            parts = text.split("\r\n\r\n", 2)
            if len(parts) < 3:
                logger.warning("Could not find HTML content in WARC record")
                return None

            # The HTML content is in the third part (after WARC headers and HTTP headers)
            html_content = parts[2]

            # Sometimes there are additional headers, look for HTML start
            html_markers = ["<!DOCTYPE", "<html", "<HTML", "<head", "<body"]
            html_start = -1

            for marker in html_markers:
                pos = html_content.find(marker)
                if pos != -1 and (html_start == -1 or pos < html_start):
                    html_start = pos

            if html_start != -1:
                return html_content[html_start:]
            else:
                # Return as-is if no clear HTML markers found
                return html_content

        except Exception as e:
            logger.error(f"Error extracting HTML from WARC: {e}")
            return None

    def clean_html_text(
        self, html: str, base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract and clean text content from HTML.

        Args:
            html: HTML content string
            base_url: Base URL for resolving relative links

        Returns:
            Dictionary containing cleaned text, title, and metadata
        """
        if not HAS_BS4:
            return self._fallback_html_cleaning(html)

        try:
            soup = BeautifulSoup(html, "html.parser")

            # Extract title
            title_tag = soup.find("title")
            title = title_tag.get_text().strip() if title_tag else ""

            # Extract meta description
            meta_desc = ""
            desc_tag = soup.find("meta", attrs={"name": "description"})
            if desc_tag and desc_tag.get("content"):
                meta_desc = desc_tag.get("content").strip()

            # Remove unwanted elements
            for tag_name in self.remove_tags:
                for tag in soup.find_all(tag_name):
                    tag.decompose()

            # Remove comments
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()

            # Extract main content areas (prioritize content-rich sections)
            content_selectors = [
                "main",
                "article",
                '[role="main"]',
                ".content",
                ".main-content",
                ".post-content",
                ".entry-content",
                ".article-content",
                ".page-content",
                "#content",
                "#main-content",
                "#post-content",
            ]

            main_content = None
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    main_content = elements[0]
                    break

            # If no main content area found, use body
            if not main_content:
                main_content = soup.find("body") or soup

            # Extract text from main content
            text_content = main_content.get_text(separator="\n", strip=True)

            # Clean up the text and filter out URL-heavy content
            cleaned_text = self._clean_text(text_content)

            # Additional filtering: if text is mostly URLs, try to extract better content
            if self._is_mostly_urls(cleaned_text):
                # Try to extract text from paragraphs and divs only
                paragraphs = main_content.find_all(["p", "div", "section", "article"])
                text_parts = []
                for p in paragraphs:
                    # Skip elements that are primarily links
                    links_in_p = p.find_all("a")
                    text_in_p = p.get_text(separator=" ", strip=True)
                    if (
                        text_in_p and len(links_in_p) < 3
                    ):  # Less than 3 links per paragraph
                        text_parts.append(text_in_p)

                if text_parts:
                    cleaned_text = self._clean_text("\n".join(text_parts))

            # Extract links for context
            links = []
            for link in soup.find_all("a", href=True):
                href = link.get("href")
                link_text = link.get_text().strip()
                if href and link_text and len(link_text) > 2:
                    if base_url:
                        href = urljoin(base_url, href)
                    links.append({"url": href, "text": link_text})

            return {
                "title": title,
                "meta_description": meta_desc,
                "text": cleaned_text,
                "links": links[:10],  # Limit to top 10 links
                "word_count": len(cleaned_text.split()),
                "char_count": len(cleaned_text),
            }

        except Exception as e:
            logger.error(f"Error cleaning HTML: {e}")
            return self._fallback_html_cleaning(html)

    def _fallback_html_cleaning(self, html: str) -> Dict[str, Any]:
        """Fallback HTML cleaning without BeautifulSoup."""
        # Extract title
        title_match = re.search(
            r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL
        )
        title = title_match.group(1).strip() if title_match else ""

        # Remove script and style tags with their content
        html = re.sub(
            r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.IGNORECASE | re.DOTALL
        )

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html)

        # Decode HTML entities
        text = (
            text.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
        )
        text = re.sub(r"&[a-zA-Z0-9]+;", "", text)  # Remove other entities

        # Clean up text
        cleaned_text = self._clean_text(text)

        return {
            "title": title,
            "meta_description": "",
            "text": cleaned_text,
            "links": [],
            "word_count": len(cleaned_text.split()),
            "char_count": len(cleaned_text),
        }

    def _clean_text(self, text: str) -> str:
        """Apply text cleaning patterns."""
        # Apply cleanup patterns
        for pattern, replacement in self.cleanup_patterns:
            text = re.sub(pattern, replacement, text)

        # Remove very short lines (likely navigation/UI elements)
        lines = text.split("\n")
        meaningful_lines = []
        for line in lines:
            line = line.strip()
            # Skip lines that are mostly URLs
            if self._is_mostly_urls(line):
                continue
            # Skip very short lines and UI text
            if len(line) > 10 and not self._is_likely_ui_text(line):
                meaningful_lines.append(line)

        return "\n".join(meaningful_lines)

    def _is_likely_ui_text(self, text: str) -> bool:
        """Check if text is likely UI/navigation rather than content."""
        ui_indicators = [
            "click here",
            "read more",
            "continue reading",
            "next page",
            "previous page",
            "home",
            "about",
            "contact",
            "privacy policy",
            "terms of service",
            "subscribe",
            "login",
            "register",
            "sign up",
            "follow us",
            "share",
            "tweet",
            "facebook",
            "instagram",
        ]

        text_lower = text.lower()
        # If text is very short and contains UI indicators
        if len(text) < 50:
            return any(indicator in text_lower for indicator in ui_indicators)

        return False

    def _is_mostly_urls(self, text: str) -> bool:
        """Check if text is mostly URLs."""
        # Count URLs and domain-like patterns
        url_pattern = r"https?://[^\s]+|www\.[^\s]+|\.[a-z]{2,6}(/|$)"
        urls = re.findall(url_pattern, text, re.IGNORECASE)

        # Count words that are not URLs
        words = text.split()

        # If more than 50% of the content is URLs, it's mostly URLs
        if len(words) > 0:
            url_ratio = len(urls) / len(words)
            return url_ratio > 0.5

        return False

    def chunk_text(
        self, text: str, chunk_size: int = 1000, overlap: int = 100
    ) -> List[str]:
        """Split text into chunks for embedding.

        Args:
            text: Text to chunk
            chunk_size: Target chunk size in characters
            overlap: Characters to overlap between chunks

        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            if end >= len(text):
                # Last chunk
                chunks.append(text[start:])
                break

            # Try to break at sentence boundary
            sentence_end = text.rfind(".", start, end)
            if sentence_end > start + chunk_size // 2:
                end = sentence_end + 1

            chunks.append(text[start:end])
            start = end - overlap

        return [chunk.strip() for chunk in chunks if chunk.strip()]

    def process_warc_record(
        self,
        warc_content: bytes,
        base_url: Optional[str] = None,
        include_chunks: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Process a complete WARC record to extract clean text.

        Args:
            warc_content: Raw WARC record bytes
            base_url: Base URL for the content
            include_chunks: Whether to include text chunks in the result

        Returns:
            Dictionary with processed content or None if processing fails
        """
        # Extract HTML from WARC
        html = self.extract_html_from_warc(warc_content)
        if not html:
            return None

        # Clean the HTML
        result = self.clean_html_text(html, base_url)

        # Only return if we have meaningful content
        # Be more lenient if we have a title and some content
        min_words = 5 if result.get("title") else 10
        if result["word_count"] < min_words:
            logger.info(
                f"Skipping content with too few words ({result['word_count']} < {min_words})"
            )
            return None

        # Add chunks for embedding only if requested
        if include_chunks and result["text"]:
            result["chunks"] = self.chunk_text(result["text"])
        else:
            result["chunks"] = []

        return result

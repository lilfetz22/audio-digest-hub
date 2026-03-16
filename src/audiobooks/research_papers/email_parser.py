"""Email parser for extracting paper references from Gmail (Arxiv + HuggingFace)."""

import base64
import datetime
import logging
import re
from typing import List, Optional

from bs4 import BeautifulSoup

from .interfaces import PaperSource
from .models import PaperReference

logger = logging.getLogger(__name__)


class ArxivHFEmailParser(PaperSource):
    """Parses Arxiv and HuggingFace emails from Gmail to extract paper references."""

    def __init__(
        self,
        arxiv_senders: List[str],
        huggingface_senders: List[str],
    ):
        self.arxiv_senders = [s.lower() for s in arxiv_senders]
        self.huggingface_senders = [s.lower() for s in huggingface_senders]

    def fetch_papers(
        self, date_str: str, gmail_service=None
    ) -> List[PaperReference]:
        """Fetch paper references from Gmail for Arxiv and HuggingFace emails.

        Args:
            date_str: Date in YYYY-MM-DD format.
            gmail_service: Authenticated Gmail API service object.

        Returns:
            Deduplicated list of PaperReference objects.
        """
        if gmail_service is None:
            raise ValueError("gmail_service is required")

        all_senders = self.arxiv_senders + self.huggingface_senders
        if not all_senders:
            return []

        messages = self._query_gmail(gmail_service, all_senders, date_str)
        if not messages:
            return []

        papers: List[PaperReference] = []
        seen_urls: set = set()

        for msg_info in messages:
            msg = (
                gmail_service.users()
                .messages()
                .get(userId="me", id=msg_info["id"])
                .execute()
            )
            sender_email = self._extract_sender(msg)
            html_body = self._extract_html_body(msg)
            if not html_body:
                continue

            if sender_email in self.arxiv_senders:
                extracted = self._parse_arxiv_email(html_body)
            elif sender_email in self.huggingface_senders:
                extracted = self._parse_huggingface_email(html_body)
            else:
                continue

            for paper in extracted:
                if paper.url not in seen_urls:
                    seen_urls.add(paper.url)
                    papers.append(paper)

        logger.info(
            f"Extracted {len(papers)} unique papers from {len(messages)} email(s)"
        )
        return papers

    def _query_gmail(self, service, senders: List[str], date_str: str) -> list:
        """Query Gmail for emails from specified senders on a given date."""
        sender_query = " OR ".join([f"from:{email}" for email in senders])
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        after_date = target_date.strftime("%Y/%m/%d")
        before_date = (target_date + datetime.timedelta(days=1)).strftime("%Y/%m/%d")
        query = f"({sender_query}) after:{after_date} before:{before_date}"

        logger.info(f"Gmail query: {query}")
        try:
            results = (
                service.users().messages().list(userId="me", q=query).execute()
            )
            messages = results.get("messages", [])
            logger.info(f"Found {len(messages)} email(s)")
            return messages
        except Exception as e:
            logger.error(f"Gmail query failed: {e}", exc_info=True)
            return []

    def _extract_sender(self, msg: dict) -> str:
        """Extract the sender email address from a Gmail message."""
        headers = msg.get("payload", {}).get("headers", [])
        for h in headers:
            if h["name"] == "From":
                match = re.search(r"<(.+?)>", h["value"])
                if match:
                    return match.group(1).lower()
                return h["value"].lower()
        return ""

    def _extract_html_body(self, msg: dict) -> Optional[str]:
        """Extract the HTML body from a Gmail message."""
        payload = msg.get("payload", {})
        try:
            if "parts" in payload:
                for part in payload["parts"]:
                    if part.get("mimeType") in ("text/html", "text/plain"):
                        data = base64.urlsafe_b64decode(part["body"]["data"])
                        return data.decode("utf-8", errors="replace")
            elif "body" in payload and "data" in payload.get("body", {}):
                data = base64.urlsafe_b64decode(payload["body"]["data"])
                return data.decode("utf-8", errors="replace")
        except Exception as e:
            logger.error(f"Failed to extract email body: {e}", exc_info=True)
        return None

    def _parse_arxiv_email(self, html: str) -> List[PaperReference]:
        """Parse an Arxiv daily digest email to extract papers with titles and abstracts."""
        papers = []
        soup = BeautifulSoup(html, "html.parser")

        # Find all arxiv URLs in the email
        arxiv_urls = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            match = re.search(r"https?://arxiv\.org/abs/(\d+\.\d+)", href)
            if match:
                arxiv_urls.add(match.group(0))

        # Also search raw text for arxiv URLs not in links
        text_urls = re.findall(r"https?://arxiv\.org/abs/\d+\.\d+", html)
        arxiv_urls.update(text_urls)

        # Try to extract structured title+abstract blocks
        # Common Arxiv email format: <b>Title:</b> ... <b>Abstract:</b> ...
        paper_blocks = self._extract_arxiv_blocks(soup, html)

        # Match URLs to blocks by arxiv ID
        for url in sorted(arxiv_urls):
            arxiv_id = re.search(r"(\d+\.\d+)", url)
            if not arxiv_id:
                continue
            aid = arxiv_id.group(1)

            title = ""
            abstract = ""
            if aid in paper_blocks:
                title = paper_blocks[aid].get("title", "")
                abstract = paper_blocks[aid].get("abstract", "")

            papers.append(
                PaperReference(
                    url=url,
                    title=title or f"Arxiv Paper {aid}",
                    abstract=abstract,
                    source="arxiv",
                )
            )

        return papers

    def _extract_arxiv_blocks(self, soup: BeautifulSoup, html: str) -> dict:
        """Extract title+abstract blocks from Arxiv email, keyed by arxiv ID."""
        blocks = {}

        # Strategy 1: Look for <h3> tags with arXiv IDs followed by Title/Abstract bold tags
        for h3 in soup.find_all("h3"):
            h3_text = h3.get_text()
            id_match = re.search(r"(\d+\.\d+)", h3_text)
            if not id_match:
                continue
            arxiv_id = id_match.group(1)

            # Collect sibling text until next h3
            title = ""
            abstract = ""
            for sibling in h3.next_siblings:
                if sibling.name == "h3":
                    break
                text = sibling.get_text() if hasattr(sibling, "get_text") else str(sibling)

                # Check for Title: pattern
                title_match = re.search(r"Title:\s*(.+)", text)
                if title_match:
                    title = title_match.group(1).strip()

                # Check for Abstract: pattern
                abs_match = re.search(r"Abstract:\s*(.+)", text, re.DOTALL)
                if abs_match:
                    abstract = abs_match.group(1).strip()

            blocks[arxiv_id] = {"title": title, "abstract": abstract}

        if blocks:
            return blocks

        # Strategy 2: Line-by-line parser for plain-text Arxiv digest format.
        # Format per paper:
        #   \\
        #   arXiv:XXXX.XXXXX
        #   Date: ...
        #
        #   Title: ... (may wrap across lines, continuation indented with spaces)
        #   Authors: ...
        #   Categories: ...
        #   \\
        #     Abstract text here...
        #   \\ ( https://arxiv.org/abs/XXXX.XXXXX , NNkb)
        #   ----...----
        raw_text = soup.get_text()
        current_id = None
        title_lines: list = []
        abstract_lines: list = []
        in_title = False
        in_abstract = False
        metadata_labels = re.compile(
            r"^(Authors?|Categories|Comments|Journal-ref|DOI|Report-no|License|Related|Proxy):",
            re.IGNORECASE,
        )

        for line in raw_text.splitlines():
            stripped = line.strip()

            # New paper block starts with "arXiv:XXXX.XXXXX"
            id_match = re.match(r"arXiv:(\d+\.\d+)", stripped)
            if id_match:
                # Save the previous block
                if current_id:
                    blocks[current_id] = {
                        "title": " ".join(title_lines).strip(),
                        "abstract": " ".join(abstract_lines).strip(),
                    }
                current_id = id_match.group(1)
                title_lines = []
                abstract_lines = []
                in_title = False
                in_abstract = False
                continue

            if current_id is None:
                continue

            # "Title:" starts the title section
            title_match = re.match(r"Title:\s*(.*)", stripped)
            if title_match:
                in_title = True
                in_abstract = False
                first = title_match.group(1).strip()
                if first:
                    title_lines = [first]
                else:
                    title_lines = []
                continue

            # Metadata labels end the title, don't start abstract
            if metadata_labels.match(stripped):
                in_title = False
                in_abstract = False
                continue

            # A standalone "\\" after we have a title signals start of abstract
            if stripped == "\\\\":
                if title_lines and not in_abstract:
                    in_abstract = True
                    in_title = False
                elif in_abstract:
                    # Second "\\" closes the abstract
                    in_abstract = False
                continue

            # "\\ ( URL )" line closes the abstract
            if re.match(r"\\\\.*https?://", stripped):
                in_abstract = False
                continue

            # Lines of dashes are separators — reset state
            if re.match(r"-{10,}", stripped):
                in_title = False
                in_abstract = False
                continue

            # Continuation of the title (indented line before Authors:)
            if in_title and line.startswith("  ") and stripped:
                title_lines.append(stripped)
                continue

            # Abstract body lines (indented with spaces in the original email)
            if in_abstract and stripped:
                abstract_lines.append(stripped)

        # Save the last block
        if current_id:
            blocks[current_id] = {
                "title": " ".join(title_lines).strip(),
                "abstract": " ".join(abstract_lines).strip(),
            }

        return blocks


    def _parse_huggingface_email(self, html: str) -> List[PaperReference]:
        """Parse a HuggingFace email to extract paper references."""
        papers = []
        soup = BeautifulSoup(html, "html.parser")

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            match = re.search(
                r"https?://huggingface\.co/papers/(\d+\.\d+)", href
            )
            if match:
                title = a_tag.get_text(strip=True) or f"HF Paper {match.group(1)}"
                url = match.group(0)

                # Try to get abstract from adjacent text
                abstract = ""
                next_p = a_tag.find_next("p")
                if next_p:
                    abstract = next_p.get_text(strip=True)

                papers.append(
                    PaperReference(
                        url=url,
                        title=title,
                        abstract=abstract,
                        source="huggingface",
                    )
                )

        return papers

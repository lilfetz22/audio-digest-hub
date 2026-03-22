"""Cumulative feedback system — preference profile management + Supabase client."""

import datetime
import json
import logging
import os
from typing import List

import requests
from google import genai
from google.genai import types

from .interfaces import FeedbackStore

logger = logging.getLogger(__name__)

MAX_EXAMPLE_PAPERS = 50


class PreferenceProfileManager(FeedbackStore):
    """Manages a cumulative preference profile stored as a local JSON file."""

    def __init__(
        self,
        profile_path: str = "preference_profile.json",
        api_key: str = "",
        model_name: str = "gemini-3-flash-preview",
    ):
        self.profile_path = profile_path
        self.api_key = api_key
        self.model_name = model_name

    def load_profile(self) -> str:
        """Load and format the preference profile for prompt injection.

        Returns:
            Formatted string describing preferences, or empty string if no profile.
        """
        profile = self._read_profile()
        if not profile:
            return ""

        interests = profile.get("interests_learned", [])
        examples = profile.get("example_papers", [])

        if not interests and not examples:
            return ""

        parts = []
        if examples:
            paper_list = "; ".join(
                [f'"{p["title"]}"' for p in examples[-10:]]  # Last 10 for brevity
            )
            parts.append(
                f"The user has previously shown interest in papers like: {paper_list}."
            )

        if interests:
            interest_list = ", ".join(interests)
            parts.append(f"Patterns noticed: {interest_list}.")

        parts.append("Prioritize papers similar to these.")
        return " ".join(parts)

    def update_profile(self, clicked_papers: List[dict]) -> None:
        """Update the profile with newly clicked papers.

        Args:
            clicked_papers: List of dicts with 'title' and 'abstract' keys.
        """
        if not clicked_papers:
            return

        profile = self._read_profile() or {
            "interests_learned": [],
            "example_papers": [],
            "updated_at": "",
        }

        # Add clicked papers as examples
        today = datetime.date.today().isoformat()
        for paper in clicked_papers:
            profile["example_papers"].append(
                {
                    "title": paper["title"],
                    "abstract": paper.get("abstract", ""),
                    "date": today,
                }
            )

        # Cap at MAX_EXAMPLE_PAPERS (keep most recent)
        if len(profile["example_papers"]) > MAX_EXAMPLE_PAPERS:
            profile["example_papers"] = profile["example_papers"][
                -MAX_EXAMPLE_PAPERS:
            ]

        # Use Gemini Flash to extract interest patterns
        new_interests = self._extract_interests(clicked_papers)
        if new_interests:
            profile["interests_learned"].extend(new_interests)
            # Deduplicate interests
            profile["interests_learned"] = list(
                dict.fromkeys(profile["interests_learned"])
            )

        profile["updated_at"] = datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat()

        self._write_profile(profile)
        logger.info(
            f"Updated preference profile: {len(profile['example_papers'])} examples, "
            f"{len(profile['interests_learned'])} interests"
        )

    def _extract_interests(self, papers: List[dict]) -> List[str]:
        """Use Gemini Flash to extract interest patterns from clicked papers."""
        if not self.api_key or self.api_key == "your-gemini-api-key":
            return []

        titles_abstracts = "\n".join(
            f"- {p['title']}: {p.get('abstract', '')}" for p in papers
        )

        try:
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=(
                    f"Extract 1-3 broad interest areas from these research papers "
                    f"the user clicked on:\n{titles_abstracts}\n\n"
                    f"Return a JSON array of short interest strings."
                ),
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )

            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            interests = json.loads(text)
            if isinstance(interests, list):
                return [str(i) for i in interests]

        except Exception as e:
            logger.warning(f"Failed to extract interests: {e}")

        return []

    def _read_profile(self) -> dict | None:
        """Read the profile JSON file."""
        if not os.path.exists(self.profile_path):
            return None
        try:
            with open(self.profile_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read profile: {e}")
            return None

    def _write_profile(self, profile: dict) -> None:
        """Write the profile JSON file."""
        try:
            with open(self.profile_path, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2)
        except OSError as e:
            logger.error(f"Failed to write profile: {e}")


class FeedbackClient:
    """Fetches click feedback data from the Supabase edge function."""

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key

    def fetch_clicked_papers(self, days: int = 30) -> List[dict]:
        """Fetch papers that were clicked in the last N days.

        Args:
            days: Number of days to look back.

        Returns:
            List of dicts with 'title' and 'abstract' for clicked papers.
        """
        url = f"{self.api_url}/research-papers?feedback=true&days={days}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                logger.warning(
                    f"Feedback API returned {response.status_code}"
                )
                return []

            data = response.json()
            clicked = []
            for day_data in data:
                for paper in day_data.get("papers", []):
                    if paper.get("clicked"):
                        clicked.append(
                            {
                                "title": paper.get("title", ""),
                                "abstract": paper.get("abstract", ""),
                            }
                        )

            logger.info(f"Fetched {len(clicked)} clicked papers from last {days} days")
            return clicked

        except Exception as e:
            logger.error(f"Failed to fetch feedback: {e}")
            return []

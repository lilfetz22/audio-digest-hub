"""Tests for feedback.py — PreferenceProfileManager + FeedbackClient."""

import json
import pytest
from unittest.mock import patch, MagicMock
from research_papers.feedback import PreferenceProfileManager, FeedbackClient


@pytest.fixture
def tmp_profile(tmp_path):
    """Create a temporary profile file path."""
    return str(tmp_path / "preference_profile.json")


@pytest.fixture
def manager(tmp_profile):
    return PreferenceProfileManager(
        profile_path=tmp_profile,
        api_key="test-key",
    )


@pytest.fixture
def sample_profile():
    return {
        "interests_learned": [
            "retrieval-augmented generation",
            "graph neural networks for optimization",
        ],
        "example_papers": [
            {
                "title": "RAG for Time Series",
                "abstract": "Combining retrieval with forecasting.",
                "date": "2026-03-10",
            },
            {
                "title": "GNN Optimization",
                "abstract": "Using GNNs for combinatorial optimization.",
                "date": "2026-03-12",
            },
        ],
        "updated_at": "2026-03-12T10:00:00Z",
    }


class TestLoadProfile:
    """Tests for loading the preference profile."""

    def test_cold_start_empty_profile(self, manager, tmp_profile):
        """Should return empty string when no profile exists."""
        result = manager.load_profile()
        assert result == ""

    def test_loads_existing_profile(self, manager, tmp_profile, sample_profile):
        """Should load and format an existing profile."""
        with open(tmp_profile, "w") as f:
            json.dump(sample_profile, f)

        result = manager.load_profile()
        assert "retrieval-augmented generation" in result
        assert "RAG for Time Series" in result

    def test_formatted_for_prompt_injection(self, manager, tmp_profile, sample_profile):
        """Output should be formatted as natural language for the scorer prompt."""
        with open(tmp_profile, "w") as f:
            json.dump(sample_profile, f)

        result = manager.load_profile()
        assert isinstance(result, str)
        assert len(result) > 0


class TestUpdateProfile:
    """Tests for updating the preference profile."""

    @patch("research_papers.feedback.genai")
    def test_update_with_new_papers(self, mock_genai, manager, tmp_profile):
        """Should add clicked papers to the profile."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '["multi-agent planning"]'
        mock_client.models.generate_content.return_value = mock_response

        clicked = [
            {"title": "Multi-Agent Planning", "abstract": "A new approach to planning."}
        ]
        manager.update_profile(clicked)

        # Verify profile was written
        with open(tmp_profile) as f:
            profile = json.load(f)

        assert len(profile["example_papers"]) == 1
        assert profile["example_papers"][0]["title"] == "Multi-Agent Planning"

    @patch("research_papers.feedback.genai")
    def test_cumulative_growth(self, mock_genai, manager, tmp_profile, sample_profile):
        """Should append to existing profile, not replace."""
        with open(tmp_profile, "w") as f:
            json.dump(sample_profile, f)

        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = '["new interest area"]'
        mock_client.models.generate_content.return_value = mock_response

        clicked = [{"title": "New Paper", "abstract": "New abstract."}]
        manager.update_profile(clicked)

        with open(tmp_profile) as f:
            profile = json.load(f)

        # Should have old + new entries
        assert len(profile["example_papers"]) == 3
        assert len(profile["interests_learned"]) == 3

    @patch("research_papers.feedback.genai")
    def test_caps_at_50_examples(self, mock_genai, manager, tmp_profile):
        """Should cap example_papers at 50 most recent entries."""
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = '["interest"]'
        mock_client.models.generate_content.return_value = mock_response

        # Pre-fill with 49 papers
        existing = {
            "interests_learned": [],
            "example_papers": [
                {"title": f"Paper {i}", "abstract": f"Abstract {i}", "date": "2026-03-01"}
                for i in range(49)
            ],
            "updated_at": "2026-03-01T00:00:00Z",
        }
        with open(tmp_profile, "w") as f:
            json.dump(existing, f)

        # Add 5 more
        clicked = [
            {"title": f"New Paper {i}", "abstract": f"New abstract {i}"}
            for i in range(5)
        ]
        manager.update_profile(clicked)

        with open(tmp_profile) as f:
            profile = json.load(f)

        # Should cap at 50
        assert len(profile["example_papers"]) == 50
        # Most recent should be the new papers
        assert profile["example_papers"][-1]["title"] == "New Paper 4"


class TestFeedbackClient:
    """Tests for FeedbackClient that fetches click data from Supabase."""

    @patch("research_papers.feedback.requests")
    def test_fetches_recent_clicks(self, mock_requests):
        """Should fetch clicked papers from Supabase edge function."""
        client = FeedbackClient(
            api_url="https://example.supabase.co/functions/v1",
            api_key="test-key",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "date": "2026-03-13",
                "papers": [
                    {"title": "Clicked Paper", "abstract": "Abstract", "clicked": True},
                    {"title": "Not Clicked", "abstract": "Abstract", "clicked": False},
                ],
            }
        ]
        mock_requests.get.return_value = mock_response

        clicked = client.fetch_clicked_papers(days=30)
        assert len(clicked) == 1
        assert clicked[0]["title"] == "Clicked Paper"

    @patch("research_papers.feedback.requests")
    def test_handles_api_error(self, mock_requests):
        """Should return empty list on API error."""
        client = FeedbackClient(
            api_url="https://example.supabase.co/functions/v1",
            api_key="test-key",
        )

        mock_requests.get.side_effect = Exception("Network error")

        clicked = client.fetch_clicked_papers(days=30)
        assert clicked == []

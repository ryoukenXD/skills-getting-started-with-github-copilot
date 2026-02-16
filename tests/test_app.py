"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    original_participants = {
        activity: details["participants"].copy()
        for activity, details in activities.items()
    }
    
    yield
    
    # Reset after test
    for activity, details in activities.items():
        details["participants"] = original_participants[activity]


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Test that all activities are returned"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 9
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
    
    def test_get_activities_includes_activity_details(self, client, reset_activities):
        """Test that activity details are included"""
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
    
    def test_get_activities_includes_participants(self, client, reset_activities):
        """Test that participants are included in the response"""
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        assert len(chess_club["participants"]) > 0
        assert "michael@mergington.edu" in chess_club["participants"]


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_for_activity_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        assert "Signed up newstudent@mergington.edu for Chess Club" in response.json()["message"]
        
        # Verify participant was added
        assert "newstudent@mergington.edu" in activities["Chess Club"]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client, reset_activities):
        """Test signup for non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent Club/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
    
    def test_signup_duplicate_participant(self, client, reset_activities):
        """Test that duplicate signup is prevented"""
        email = "michael@mergington.edu"  # Already registered for Chess Club
        
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Student already signed up"
    
    def test_signup_increases_participant_count(self, client, reset_activities):
        """Test that signup increases the participant count"""
        initial_count = len(activities["Programming Class"]["participants"])
        
        client.post(
            "/activities/Programming Class/signup",
            params={"email": "newprogrammer@mergington.edu"}
        )
        
        final_count = len(activities["Programming Class"]["participants"])
        assert final_count == initial_count + 1
    
    def test_signup_multiple_different_activities(self, client, reset_activities):
        """Test signing up for multiple different activities"""
        email = "versatile@mergington.edu"
        
        response1 = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        response2 = client.post(
            "/activities/Art Studio/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Verify registered in both
        assert email in activities["Chess Club"]["participants"]
        assert email in activities["Art Studio"]["participants"]


class TestUnregisterFromActivity:
    """Tests for POST /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregister from an activity"""
        email = "michael@mergington.edu"  # Already registered for Chess Club
        initial_count = len(activities["Chess Club"]["participants"])
        
        response = client.post(
            "/activities/Chess Club/unregister",
            params={"email": email}
        )
        assert response.status_code == 200
        assert f"Unregistered {email} from Chess Club" in response.json()["message"]
        
        # Verify participant was removed
        assert email not in activities["Chess Club"]["participants"]
        assert len(activities["Chess Club"]["participants"]) == initial_count - 1
    
    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test unregister from non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent Club/unregister",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
    
    def test_unregister_not_registered_participant(self, client, reset_activities):
        """Test unregister for non-registered participant returns 400"""
        response = client.post(
            "/activities/Chess Club/unregister",
            params={"email": "notregistered@mergington.edu"}
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Student is not registered"
    
    def test_unregister_then_signup_again(self, client, reset_activities):
        """Test that a student can re-signup after unregistering"""
        email = "testuser@mergington.edu"
        activity = "Chess Club"
        
        # Sign up
        response1 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        assert email in activities[activity]["participants"]
        
        # Unregister
        response2 = client.post(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert response2.status_code == 200
        assert email not in activities[activity]["participants"]
        
        # Sign up again
        response3 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response3.status_code == 200
        assert email in activities[activity]["participants"]


class TestEdgeCases:
    """Tests for edge cases and special scenarios"""
    
    def test_email_with_special_characters(self, client, reset_activities):
        """Test signup with email containing special characters"""
        email = "john.doe+test@mergington.edu"
        
        response = client.post(
            "/activities/Tennis Club/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        assert email in activities["Tennis Club"]["participants"]
    
    def test_activity_name_with_special_characters(self, client, reset_activities):
        """Test that activity names with spaces are handled correctly"""
        response = client.post(
            "/activities/Programming Class/signup",
            params={"email": "coder@mergington.edu"}
        )
        assert response.status_code == 200
    
    def test_get_activities_structure(self, client, reset_activities):
        """Test that activity data structure is consistent"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert isinstance(activity_name, str)
            assert isinstance(activity_data, dict)
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert isinstance(activity_data["max_participants"], int)
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)

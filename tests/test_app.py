import pytest
from unittest.mock import patch, MagicMock
import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock OpenAI client before importing app to avoid API key issues during import if not set
with patch('openai.OpenAI'):
    # We also need to mock os.getenv if the real .env isn't there or we want to bypass the check
    # But app.py checks if not OPENAI_API_KEY: raise ...
    # We can set a dummy env var before import
    os.environ['OPENAI_API_KEY'] = 'dummy'
    from app import app, match_course_info, match_faq, should_ask_phone, generate_ai_reply

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    rv = client.get('/')
    assert rv.status_code == 200
    assert b"OK" in rv.data

def test_match_course_info():
    # Test with a keyword that should match "Стратегийн Дижитал Маркетер"
    assert match_course_info("дижитал маркетинг") is not None
    # Test with a keyword that should match "Data Analyst"
    assert match_course_info("өгөгдлийн шинжээч") is not None
    # Test with non-matching string
    assert match_course_info("random string") is None

def test_match_faq():
    # Test address faq
    assert match_faq("хаяг") is not None
    # Test phone faq
    assert match_faq("утас") is not None
    # Test non-matching
    assert match_faq("random string") is None

def test_should_ask_phone():
    # Cases where it should return True
    assert should_ask_phone("бүртгүүлье") is True
    assert should_ask_phone("элсэх") is True
    # Cases where it should return False
    assert should_ask_phone("сайн байна уу") is False

@patch('app.client.chat.completions.create')
def test_openai_fallback(mock_create):
    # Setup mock response
    mock_choice = MagicMock()
    mock_choice.message.content = "AI Reply"
    mock_create.return_value.choices = [mock_choice]
    
    reply = generate_ai_reply("random question")
    assert reply == "AI Reply"

def test_manychat_endpoint_course_match(client):
    # Test endpoint with text that matches a course (no AI call needed)
    rv = client.post('/manychat-ai', json={'text': 'data analyst'})
    assert rv.status_code == 200
    json_data = rv.get_json()
    assert "Data Analyst" in json_data['reply']
    assert json_data['ask_phone'] is False

def test_manychat_endpoint_ask_phone(client):
    # Test endpoint with text that triggers phone ask
    rv = client.post('/manychat-ai', json={'text': 'бүртгүүлмээр байна'})
    assert rv.status_code == 200
    json_data = rv.get_json()
    assert json_data['ask_phone'] is True

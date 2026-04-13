import os
import sys
import unittest
from unittest.mock import MagicMock, mock_open, patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from services.audio_generator import AudioGenerationService


class TestAudioGenerationService(unittest.TestCase):
    def setUp(self):
        self.mock_config = MagicMock()
        self.mock_config.tts_api_key = "test_key"
        self.mock_config.audio_output_dir = "./test_output"
        self.mock_config.tts_base_url = "http://test.api/tts"
        self.mock_config.tts_model = "test-tts"
        self.mock_config.ffmpeg_path = "ffmpeg"

        # Patch Path.mkdir to avoid actual filesystem creation during init
        with patch('pathlib.Path.mkdir'):
            self.service = AudioGenerationService(self.mock_config)

    @patch('requests.post')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    def test_generate_audio_success(self, mock_exists, mock_file, mock_post):
        # Setup mocks
        mock_exists.return_value = False # File doesn't exist
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"audio_data"
        mock_post.return_value = mock_response
        
        script = [
            {"role": "Host", "content": "Hello world"},
            {"role": "Guest", "content": "Hi host"}
        ]
        
        # Execute
        files = self.service.generate_audio(script, "task_123")
        
        # Verify
        self.assertEqual(len(files), 2)
        self.assertTrue(files[0].endswith("task_123_000_Host.mp3"))
        self.assertTrue(files[1].endswith("task_123_001_Guest.mp3"))
        
        # Verify API calls
        self.assertEqual(mock_post.call_count, 2)
        
        # Check first call arguments
        args, kwargs = mock_post.call_args_list[0]
        self.assertEqual(kwargs['json']['voice'], 'xiayu')
        self.assertEqual(kwargs['json']['input'], 'Hello world')
        
        # Check second call arguments
        args, kwargs = mock_post.call_args_list[1]
        self.assertEqual(kwargs['json']['voice'], 'liwa')
        self.assertEqual(kwargs['json']['input'], 'Hi host')

    def test_generate_audio_no_api_key(self):
        self.mock_config.tts_api_key = None
        script = [{"role": "Host", "content": "Hello"}]
        
        files = self.service.generate_audio(script)
        self.assertEqual(files, [])

    @patch('requests.post')
    @patch('pathlib.Path.exists')
    def test_generate_audio_api_failure(self, mock_exists, mock_post):
        mock_exists.return_value = False
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        script = [{"role": "Host", "content": "Hello"}]
        
        files = self.service.generate_audio(script)
        self.assertEqual(files, [])

    def test_get_voice_for_role(self):
        self.assertEqual(self.service._get_voice_for_role("Host"), "xiayu")
        self.assertEqual(self.service._get_voice_for_role("Xiayu"), "xiayu")
        self.assertEqual(self.service._get_voice_for_role("Guest"), "liwa")
        self.assertEqual(self.service._get_voice_for_role("Liwa"), "liwa")
        self.assertEqual(self.service._get_voice_for_role("Unknown"), "xiayu") # Default

if __name__ == '__main__':
    unittest.main()

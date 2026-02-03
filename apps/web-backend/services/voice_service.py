"""
Voice Service

Service layer for speech-to-text (STT) and text-to-speech (TTS) capabilities.
Supports hands-free pair programming through voice interaction.
Uses optional dependencies for voice libraries with graceful fallback.
"""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any, Literal
from pathlib import Path
import io

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    sr = None

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    pyttsx3 = None

logger = logging.getLogger(__name__)


class VoiceServiceError(Exception):
    """Base exception for voice service errors."""
    pass


class STTError(VoiceServiceError):
    """Exception raised for speech-to-text errors."""
    pass


class TTSError(VoiceServiceError):
    """Exception raised for text-to-speech errors."""
    pass


class SpeechToTextService:
    """
    Speech-to-Text service for converting audio input to text.

    Supports multiple recognition engines with graceful fallback.
    """

    def __init__(
        self,
        engine: Literal["google", "sphinx", "whisper"] = "google",
        language: str = "en-US",
        timeout: float = 5.0,
        phrase_time_limit: Optional[float] = None,
    ):
        """
        Initialize STT service.

        Args:
            engine: Recognition engine to use ("google", "sphinx", "whisper")
            language: Language code for recognition (e.g., "en-US")
            timeout: Maximum wait time for speech to start (seconds)
            phrase_time_limit: Maximum duration for phrase (seconds, None for unlimited)

        Raises:
            ImportError: If speech_recognition library is not installed
        """
        if not SPEECH_RECOGNITION_AVAILABLE:
            raise ImportError(
                "speech_recognition library is required for STT. "
                "Install it with: pip install SpeechRecognition"
            )

        self.engine = engine
        self.language = language
        self.timeout = timeout
        self.phrase_time_limit = phrase_time_limit

        self.recognizer: Optional[sr.Recognizer] = None
        self.microphone: Optional[sr.Microphone] = None
        self._is_initialized = False

    def initialize(self):
        """
        Initialize recognizer and microphone.

        Raises:
            STTError: If initialization fails
        """
        try:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()

            # Adjust for ambient noise
            logger.info("Calibrating microphone for ambient noise...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)

            self._is_initialized = True
            logger.info(f"STT service initialized with engine: {self.engine}")

        except Exception as e:
            raise STTError(f"Failed to initialize STT service: {e}")

    def listen(self) -> str:
        """
        Listen for speech and convert to text.

        Returns:
            Transcribed text from speech

        Raises:
            STTError: If listening or recognition fails
        """
        if not self._is_initialized:
            self.initialize()

        try:
            logger.info("Listening for speech...")

            with self.microphone as source:
                audio = self.recognizer.listen(
                    source,
                    timeout=self.timeout,
                    phrase_time_limit=self.phrase_time_limit,
                )

            logger.info(f"Processing speech with {self.engine} engine...")

            # Use appropriate recognition engine
            if self.engine == "google":
                text = self.recognizer.recognize_google(audio, language=self.language)
            elif self.engine == "sphinx":
                text = self.recognizer.recognize_sphinx(audio, language=self.language)
            elif self.engine == "whisper":
                text = self.recognizer.recognize_whisper(audio, language=self.language)
            else:
                raise STTError(f"Unsupported recognition engine: {self.engine}")

            logger.info(f"Transcribed: {text}")
            return text

        except sr.WaitTimeoutError:
            raise STTError(f"No speech detected within {self.timeout} seconds")
        except sr.UnknownValueError:
            raise STTError("Could not understand audio")
        except sr.RequestError as e:
            raise STTError(f"Recognition service error: {e}")
        except Exception as e:
            raise STTError(f"STT error: {e}")

    async def listen_async(self) -> str:
        """
        Async wrapper for listen().

        Returns:
            Transcribed text from speech

        Raises:
            STTError: If listening or recognition fails
        """
        return await asyncio.get_event_loop().run_in_executor(None, self.listen)

    def transcribe_audio_file(self, audio_file: Path) -> str:
        """
        Transcribe audio from a file.

        Args:
            audio_file: Path to audio file (WAV, FLAC, etc.)

        Returns:
            Transcribed text

        Raises:
            STTError: If transcription fails
        """
        if not self._is_initialized:
            self.initialize()

        try:
            with sr.AudioFile(str(audio_file)) as source:
                audio = self.recognizer.record(source)

            if self.engine == "google":
                text = self.recognizer.recognize_google(audio, language=self.language)
            elif self.engine == "sphinx":
                text = self.recognizer.recognize_sphinx(audio, language=self.language)
            elif self.engine == "whisper":
                text = self.recognizer.recognize_whisper(audio, language=self.language)
            else:
                raise STTError(f"Unsupported recognition engine: {self.engine}")

            return text

        except Exception as e:
            raise STTError(f"Failed to transcribe audio file: {e}")


class TextToSpeechService:
    """
    Text-to-Speech service for converting text to audio output.

    Supports multiple TTS engines with graceful fallback.
    """

    def __init__(
        self,
        engine: Literal["pyttsx3", "system"] = "pyttsx3",
        voice_id: Optional[str] = None,
        rate: int = 200,
        volume: float = 1.0,
    ):
        """
        Initialize TTS service.

        Args:
            engine: TTS engine to use ("pyttsx3" or "system")
            voice_id: Specific voice ID to use (None for default)
            rate: Speech rate in words per minute
            volume: Volume level (0.0 to 1.0)

        Raises:
            ImportError: If pyttsx3 library is not installed
        """
        if engine == "pyttsx3" and not PYTTSX3_AVAILABLE:
            raise ImportError(
                "pyttsx3 library is required for TTS. "
                "Install it with: pip install pyttsx3"
            )

        self.engine_type = engine
        self.voice_id = voice_id
        self.rate = rate
        self.volume = volume

        self.engine = None
        self._is_initialized = False

    def initialize(self):
        """
        Initialize TTS engine.

        Raises:
            TTSError: If initialization fails
        """
        try:
            if self.engine_type == "pyttsx3":
                self.engine = pyttsx3.init()

                # Configure voice properties
                self.engine.setProperty('rate', self.rate)
                self.engine.setProperty('volume', self.volume)

                # Set specific voice if provided
                if self.voice_id:
                    voices = self.engine.getProperty('voices')
                    for voice in voices:
                        if voice.id == self.voice_id:
                            self.engine.setProperty('voice', voice.id)
                            break

                self._is_initialized = True
                logger.info(f"TTS service initialized with engine: {self.engine_type}")
            else:
                raise TTSError(f"Unsupported TTS engine: {self.engine_type}")

        except Exception as e:
            raise TTSError(f"Failed to initialize TTS service: {e}")

    def speak(self, text: str, block: bool = True):
        """
        Convert text to speech and play audio.

        Args:
            text: Text to speak
            block: Whether to block until speech completes

        Raises:
            TTSError: If speech synthesis fails
        """
        if not self._is_initialized:
            self.initialize()

        try:
            logger.info(f"Speaking: {text[:50]}...")

            if self.engine_type == "pyttsx3":
                self.engine.say(text)
                if block:
                    self.engine.runAndWait()
            else:
                raise TTSError(f"Unsupported TTS engine: {self.engine_type}")

        except Exception as e:
            raise TTSError(f"TTS error: {e}")

    async def speak_async(self, text: str) -> None:
        """
        Async wrapper for speak().

        Args:
            text: Text to speak

        Raises:
            TTSError: If speech synthesis fails
        """
        await asyncio.get_event_loop().run_in_executor(
            None, self.speak, text, True
        )

    def save_to_file(self, text: str, output_file: Path):
        """
        Convert text to speech and save as audio file.

        Args:
            text: Text to convert
            output_file: Path to output audio file

        Raises:
            TTSError: If saving fails
        """
        if not self._is_initialized:
            self.initialize()

        try:
            if self.engine_type == "pyttsx3":
                self.engine.save_to_file(text, str(output_file))
                self.engine.runAndWait()
            else:
                raise TTSError(f"Unsupported TTS engine: {self.engine_type}")

        except Exception as e:
            raise TTSError(f"Failed to save audio file: {e}")

    def get_available_voices(self) -> list[Dict[str, Any]]:
        """
        Get list of available voices.

        Returns:
            List of voice information dictionaries

        Raises:
            TTSError: If retrieval fails
        """
        if not self._is_initialized:
            self.initialize()

        try:
            if self.engine_type == "pyttsx3":
                voices = self.engine.getProperty('voices')
                return [
                    {
                        'id': voice.id,
                        'name': voice.name,
                        'languages': voice.languages,
                        'gender': getattr(voice, 'gender', None),
                        'age': getattr(voice, 'age', None),
                    }
                    for voice in voices
                ]
            else:
                raise TTSError(f"Unsupported TTS engine: {self.engine_type}")

        except Exception as e:
            raise TTSError(f"Failed to get available voices: {e}")


class VoiceService:
    """
    Combined voice service providing both STT and TTS capabilities.

    Main interface for voice interaction in pair programming mode.
    """

    def __init__(
        self,
        stt_engine: Literal["google", "sphinx", "whisper"] = "google",
        tts_engine: Literal["pyttsx3", "system"] = "pyttsx3",
        language: str = "en-US",
        voice_id: Optional[str] = None,
    ):
        """
        Initialize voice service with STT and TTS.

        Args:
            stt_engine: Speech recognition engine
            tts_engine: Text-to-speech engine
            language: Language code (e.g., "en-US")
            voice_id: Specific TTS voice ID (None for default)
        """
        self.stt_engine = stt_engine
        self.tts_engine = tts_engine
        self.language = language
        self.voice_id = voice_id

        self.stt: Optional[SpeechToTextService] = None
        self.tts: Optional[TextToSpeechService] = None
        self._is_initialized = False

    def initialize(self):
        """
        Initialize both STT and TTS services.

        Raises:
            VoiceServiceError: If initialization fails
        """
        try:
            # Initialize STT
            if SPEECH_RECOGNITION_AVAILABLE:
                self.stt = SpeechToTextService(
                    engine=self.stt_engine,
                    language=self.language,
                )
                self.stt.initialize()
                logger.info("STT service ready")
            else:
                logger.warning("STT not available - speech_recognition not installed")

            # Initialize TTS
            if PYTTSX3_AVAILABLE or self.tts_engine == "system":
                self.tts = TextToSpeechService(
                    engine=self.tts_engine,
                    voice_id=self.voice_id,
                )
                self.tts.initialize()
                logger.info("TTS service ready")
            else:
                logger.warning("TTS not available - pyttsx3 not installed")

            self._is_initialized = True
            logger.info("Voice service initialized successfully")

        except Exception as e:
            raise VoiceServiceError(f"Failed to initialize voice service: {e}")

    async def listen_and_respond(
        self,
        response_callback: Optional[Callable[[str], str]] = None,
        speak_response: bool = True,
    ) -> tuple[str, Optional[str]]:
        """
        Listen for speech, process it, and optionally speak response.

        Args:
            response_callback: Async function that processes transcribed text and returns response
            speak_response: Whether to speak the response via TTS

        Returns:
            Tuple of (transcribed_text, response_text)

        Raises:
            VoiceServiceError: If voice interaction fails
        """
        if not self._is_initialized:
            self.initialize()

        if not self.stt:
            raise VoiceServiceError("STT service not available")

        try:
            # Listen and transcribe
            transcribed_text = await self.stt.listen_async()

            # Process response if callback provided
            response_text = None
            if response_callback:
                if asyncio.iscoroutinefunction(response_callback):
                    response_text = await response_callback(transcribed_text)
                else:
                    response_text = response_callback(transcribed_text)

                # Speak response if requested and TTS available
                if speak_response and response_text and self.tts:
                    await self.tts.speak_async(response_text)

            return transcribed_text, response_text

        except (STTError, TTSError) as e:
            raise VoiceServiceError(f"Voice interaction error: {e}")

    def is_available(self) -> Dict[str, bool]:
        """
        Check which voice services are available.

        Returns:
            Dictionary with 'stt' and 'tts' availability flags
        """
        return {
            'stt': SPEECH_RECOGNITION_AVAILABLE,
            'tts': PYTTSX3_AVAILABLE or self.tts_engine == "system",
        }

    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Cleanup if needed
        if self.tts and hasattr(self.tts.engine, 'stop'):
            try:
                self.tts.engine.stop()
            except Exception:
                pass

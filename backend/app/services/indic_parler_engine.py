"""
Indic Parler-TTS Engine for SaralPolicy
Provides high-quality Hindi speech synthesis using AI4Bharat's model.
Optional component - gracefully degrades if dependencies unavailable.

Model: ai4bharat/indic-parler-tts
License: Apache 2.0
Model Size: 0.9B parameters

Citations:
-----------
@inproceedings{sankar25_interspeech,
  title     = {{Rasmalai : Resources for Adaptive Speech Modeling in IndiAn Languages with Accents and Intonations}},
  author    = {Ashwin Sankar and Yoach Lacombe and Sherry Thomas and Praveen {Srinivasa Varadhan} and Sanchit Gandhi and Mitesh M. Khapra},
  year      = {2025},
  booktitle = {{Interspeech 2025}},
  pages     = {4128--4132},
  doi       = {10.21437/Interspeech.2025-2758},
}

@misc{lacombe-etal-2024-parler-tts,
  author = {Yoach Lacombe and Vaibhav Srivastav and Sanchit Gandhi},
  title = {Parler-TTS},
  year = {2024},
  publisher = {GitHub},
  howpublished = {\\url{https://github.com/huggingface/parler-tts}}
}

@misc{lyth2024natural,
  title={Natural language guidance of high-fidelity text-to-speech with synthetic annotations},
  author={Dan Lyth and Simon King},
  year={2024},
  eprint={2402.01912},
  archivePrefix={arXiv},
}
"""

import os
import re
import tempfile
import structlog
from pathlib import Path
from typing import Optional, List

logger = structlog.get_logger(__name__)


def _get_hf_token() -> Optional[str]:
    """
    Securely retrieve HuggingFace token from environment.
    
    Token sources (in priority order):
    1. HF_TOKEN environment variable
    2. HUGGING_FACE_HUB_TOKEN environment variable (legacy)
    
    Security:
    - Token is never logged or exposed in error messages
    - Token is only used for model download authentication
    - Returns None if not configured (graceful degradation)
    
    Returns:
        HuggingFace token string or None if not configured
    """
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if token:
        # Validate token format (starts with hf_)
        if not token.startswith("hf_"):
            logger.warning("HF_TOKEN format appears invalid (should start with 'hf_')")
            return None
        # Log presence without exposing value
        logger.debug("HuggingFace token configured", token_prefix=token[:5] + "...")
    return token


# Check for optional dependencies
TORCH_AVAILABLE = False
PARLER_AVAILABLE = False
SOUNDFILE_AVAILABLE = False
PYDUB_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    pass

try:
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer
    PARLER_AVAILABLE = True
except ImportError:
    pass

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    pass

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    pass


# Voice description prompts for consistent output
# Using recommended speakers from AI4Bharat: Rohit/Divya for Hindi, Thoma/Mary for English
VOICE_DESCRIPTIONS = {
    "hi": "Divya speaks with a clear, slightly expressive tone at a moderate pace. The recording is of very high quality with very clear audio and no background noise.",
    "en": "Mary speaks with a clear, neutral tone at a moderate pace. The recording is of very high quality with very clear audio and no background noise."
}

# Hindi sentence boundary pattern
HINDI_SENTENCE_PATTERN = re.compile(r'[।.!?]+')


class IndicParlerEngine:
    """
    Wrapper for AI4Bharat Indic Parler-TTS model.
    
    Provides lazy loading, text chunking, and graceful degradation.
    CPU-only inference for POC (no GPU required).
    """
    
    MODEL_ID = "ai4bharat/indic-parler-tts"
    MAX_TEXT_LENGTH = 500
    CHUNK_SIZE = 200
    SAMPLING_RATE = 44100
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.description_tokenizer = None
        self.device = self._get_device()
        self._initialized = False
        self._init_error: Optional[str] = None
        
        logger.info(
            "IndicParlerEngine created",
            torch_available=TORCH_AVAILABLE,
            parler_available=PARLER_AVAILABLE,
            soundfile_available=SOUNDFILE_AVAILABLE,
            pydub_available=PYDUB_AVAILABLE,
            device=self.device
        )
    
    def _get_device(self) -> str:
        """Determine device for inference (CPU-only for POC)."""
        # Force CPU unless explicitly enabled via env var
        if os.environ.get("INDIC_TTS_DEVICE", "cpu").lower() == "cuda":
            if TORCH_AVAILABLE and torch.cuda.is_available():
                return "cuda:0"
        return "cpu"
    
    def is_available(self) -> bool:
        """Check if all required dependencies are available."""
        if not all([TORCH_AVAILABLE, PARLER_AVAILABLE, SOUNDFILE_AVAILABLE]):
            return False
        if os.environ.get("INDIC_TTS_ENABLED", "true").lower() == "false":
            return False
        return True
    
    def initialize(self) -> bool:
        """
        Lazy-load model on first use.
        
        Uses HF_TOKEN from environment for gated model authentication.
        Token is handled securely - never logged or exposed.
        
        Returns:
            bool: True if initialization successful, False otherwise.
        """
        if self._initialized:
            return True
        
        if not self.is_available():
            self._init_error = "Required dependencies not available"
            logger.warning("IndicParlerEngine dependencies not available")
            return False
        
        try:
            logger.info("Loading Indic Parler-TTS model", model_id=self.MODEL_ID)
            
            # Get HF token for gated model access
            hf_token = _get_hf_token()
            if not hf_token:
                self._init_error = (
                    "HF_TOKEN not configured. This is a gated model requiring authentication. "
                    "Set HF_TOKEN environment variable with your HuggingFace token. "
                    "Get token from: https://huggingface.co/settings/tokens"
                )
                logger.warning(
                    "HF_TOKEN not configured for gated model access",
                    model_id=self.MODEL_ID,
                    help_url="https://huggingface.co/settings/tokens"
                )
                return False
            
            # Load model with token authentication
            self.model = ParlerTTSForConditionalGeneration.from_pretrained(
                self.MODEL_ID,
                token=hf_token
            ).to(self.device)
            
            # Load tokenizers with token authentication
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.MODEL_ID,
                token=hf_token
            )
            self.description_tokenizer = AutoTokenizer.from_pretrained(
                self.model.config.text_encoder._name_or_path,
                token=hf_token
            )
            
            self._initialized = True
            logger.info("Indic Parler-TTS model loaded successfully", device=self.device)
            return True
            
        except Exception as e:
            # Sanitize error message to avoid token exposure
            error_msg = str(e)
            if "token" in error_msg.lower() or "hf_" in error_msg:
                error_msg = "Authentication failed - check HF_TOKEN validity and model access permissions"
            self._init_error = error_msg
            logger.error("Failed to initialize Indic Parler-TTS", error=error_msg)
            return False
    
    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks at sentence boundaries.
        
        Args:
            text: Input text to chunk.
            
        Returns:
            List of text chunks, each <= CHUNK_SIZE characters.
        """
        if len(text) <= self.CHUNK_SIZE:
            return [text]
        
        chunks = []
        # Split at Hindi/English sentence boundaries
        sentences = HINDI_SENTENCE_PATTERN.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        current_chunk = ""
        for sentence in sentences:
            if len(sentence) > self.CHUNK_SIZE:
                # Split long sentence at clause boundaries
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                # Split at commas
                clauses = sentence.split(',')
                for clause in clauses:
                    clause = clause.strip()
                    if len(current_chunk) + len(clause) + 2 <= self.CHUNK_SIZE:
                        current_chunk = f"{current_chunk}, {clause}" if current_chunk else clause
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = clause[:self.CHUNK_SIZE]
            elif len(current_chunk) + len(sentence) + 2 <= self.CHUNK_SIZE:
                current_chunk = f"{current_chunk}। {sentence}" if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks if chunks else [text[:self.CHUNK_SIZE]]
    
    def generate(self, text: str, language: str = "hi") -> Optional[bytes]:
        """
        Generate audio waveform from text.
        
        Args:
            text: Text to convert to speech.
            language: Language code ('hi' for Hindi, 'en' for English).
            
        Returns:
            Audio data as WAV bytes, or None if generation fails.
        """
        if not self._initialized and not self.initialize():
            logger.warning("IndicParlerEngine not initialized")
            return None
        
        try:
            # Truncate if too long
            if len(text) > self.MAX_TEXT_LENGTH:
                text = text[:self.MAX_TEXT_LENGTH]
                logger.warning("Text truncated", max_length=self.MAX_TEXT_LENGTH)
            
            # Get voice description
            description = VOICE_DESCRIPTIONS.get(language, VOICE_DESCRIPTIONS["hi"])
            
            # Chunk text if needed
            chunks = self._chunk_text(text)
            audio_arrays = []
            
            for chunk in chunks:
                # Tokenize
                description_ids = self.description_tokenizer(
                    description, return_tensors="pt"
                ).to(self.device)
                prompt_ids = self.tokenizer(
                    chunk, return_tensors="pt"
                ).to(self.device)
                
                # Generate audio
                with torch.no_grad():
                    generation = self.model.generate(
                        input_ids=description_ids.input_ids,
                        attention_mask=description_ids.attention_mask,
                        prompt_input_ids=prompt_ids.input_ids,
                        prompt_attention_mask=prompt_ids.attention_mask
                    )
                
                audio_arr = generation.cpu().numpy().squeeze()
                audio_arrays.append(audio_arr)
            
            # Concatenate chunks
            import numpy as np
            if len(audio_arrays) > 1:
                combined_audio = np.concatenate(audio_arrays)
            else:
                combined_audio = audio_arrays[0]
            
            # Convert to WAV bytes
            import io
            wav_buffer = io.BytesIO()
            sf.write(wav_buffer, combined_audio, self.SAMPLING_RATE, format='WAV')
            wav_buffer.seek(0)
            
            logger.info("Audio generated successfully", 
                       chunks=len(chunks), 
                       duration_sec=len(combined_audio) / self.SAMPLING_RATE)
            
            return wav_buffer.read()
            
        except Exception as e:
            logger.error("Audio generation failed", error=str(e))
            return None
    
    def generate_file(self, text: str, language: str = "hi", 
                      output_format: str = "mp3") -> Optional[str]:
        """
        Generate audio file from text.
        
        Args:
            text: Text to convert to speech.
            language: Language code.
            output_format: Output format ('mp3' or 'wav').
            
        Returns:
            Path to generated audio file, or None if generation fails.
        """
        wav_data = self.generate(text, language)
        if not wav_data:
            return None
        
        try:
            import time
            temp_dir = Path(tempfile.gettempdir()) / "saralpolicy_tts"
            temp_dir.mkdir(exist_ok=True)
            
            timestamp = int(time.time() * 1000)
            
            if output_format == "mp3" and PYDUB_AVAILABLE:
                # Convert WAV to MP3
                try:
                    import io
                    wav_buffer = io.BytesIO(wav_data)
                    audio = AudioSegment.from_wav(wav_buffer)
                    
                    filepath = temp_dir / f"indic_tts_{language}_{timestamp}.mp3"
                    audio.export(str(filepath), format="mp3", bitrate="128k")
                    
                    logger.info("MP3 file generated", path=str(filepath))
                    return str(filepath)
                except Exception as e:
                    logger.warning("MP3 conversion failed, falling back to WAV", error=str(e))
            
            # Fallback to WAV
            filepath = temp_dir / f"indic_tts_{language}_{timestamp}.wav"
            with open(filepath, 'wb') as f:
                f.write(wav_data)
            
            logger.info("WAV file generated", path=str(filepath))
            return str(filepath)
            
        except Exception as e:
            logger.error("File generation failed", error=str(e))
            return None
    
    def get_status(self) -> dict:
        """Get engine status information (token values are never exposed)."""
        return {
            "available": self.is_available(),
            "initialized": self._initialized,
            "device": self.device,
            "model_id": self.MODEL_ID,
            "init_error": self._init_error,
            "hf_token_configured": _get_hf_token() is not None,
            "dependencies": {
                "torch": TORCH_AVAILABLE,
                "parler_tts": PARLER_AVAILABLE,
                "soundfile": SOUNDFILE_AVAILABLE,
                "pydub": PYDUB_AVAILABLE
            }
        }

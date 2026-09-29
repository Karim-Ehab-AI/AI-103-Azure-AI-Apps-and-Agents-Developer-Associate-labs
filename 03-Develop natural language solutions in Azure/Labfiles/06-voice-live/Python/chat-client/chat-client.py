import os
import asyncio
import base64
import queue

from dotenv import load_dotenv
import pyaudio

from azure.identity.aio import AzureCliCredential
from azure.ai.voicelive.aio import connect
from azure.ai.voicelive.models import (
    InputAudioFormat,
    Modality,
    OutputAudioFormat,
    RequestSession,
    ServerEventType,
    AudioNoiseReduction,
    AudioEchoCancellation,
    AzureSemanticVadMultilingual,
)


def main():
    """Main entry point."""

    try:
        # Clear console
        os.system("cls" if os.name == "nt" else "clear")

        # Load environment variables
        load_dotenv()

        endpoint = os.environ.get("AZURE_VOICELIVE_ENDPOINT")
        agent_name = os.environ.get("AZURE_VOICELIVE_AGENT_ID")
        project_name = os.environ.get("AZURE_VOICELIVE_PROJECT_NAME")

        # Validate configuration
        if not endpoint:
            raise ValueError("AZURE_VOICELIVE_ENDPOINT is missing from .env")

        if not agent_name:
            raise ValueError("AZURE_VOICELIVE_AGENT_ID is missing from .env")

        if not project_name:
            raise ValueError("AZURE_VOICELIVE_PROJECT_NAME is missing from .env")

        # Create Azure credential
        credential = AzureCliCredential()

        # Create Voice Assistant
        assistant = VoiceAssistant(
            endpoint=endpoint,
            credential=credential,
            agent_name=agent_name,
            project_name=project_name,
        )

        try:
            asyncio.run(assistant.start())

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")

    except Exception as e:
        print(f"❌ An error occurred: {e}")


# ============================================================
# VoiceAssistant
# ============================================================

class VoiceAssistant:
    """
    Main coordinator for the Azure Voice Live voice agent.

    Flow:
    1. Connect to Voice Live
    2. Connect to Foundry Agent
    3. Configure the session
    4. Start audio
    5. Process server events
    """

    def __init__(
        self,
        endpoint,
        credential,
        agent_name,
        project_name,
    ):
        self.endpoint = endpoint
        self.credential = credential
        self.agent_name = agent_name
        self.project_name = project_name

        self.connection = None
        self.audio_processor = None

    async def start(self):
        """Start the voice assistant."""

        print("\n" + "=" * 60)
        print("🎙️  AZURE VOICELIVE VOICE AGENT")
        print("=" * 60)

        try:
            # ====================================================
            # STEP 1: Connect Voice Live to the Foundry Agent
            # ====================================================

            async with connect(
                endpoint=self.endpoint,
                credential=self.credential,

                # Current Voice Live API version
                api_version="2026-06-01-preview",

                # Foundry Agent
                agent_name=self.agent_name,
                project_name=self.project_name,

            ) as connection:

                self.connection = connection

                print("🔗 Connected to Voice Live")

                # ====================================================
                # STEP 2: Initialize audio processor
                # ====================================================

                self.audio_processor = AudioProcessor(connection)

                # ====================================================
                # STEP 3: Configure Voice Live session
                # ====================================================

                await self.setup_session()

                # ====================================================
                # STEP 4: Start speaker
                # ====================================================

                self.audio_processor.start_playback()

                print("\n✅ Ready! Start speaking...")
                print("Press Ctrl+C to exit\n")

                # ====================================================
                # STEP 5: Process events
                # ====================================================

                await self.process_events()

        finally:

            if self.audio_processor:
                self.audio_processor.shutdown()

            await self.credential.close()

    # ========================================================
    # Session configuration
    # ========================================================

    async def setup_session(self):
        """Configure the Voice Live session."""

        session_config = RequestSession(

            # Enable text + audio
            modalities=[
                Modality.TEXT,
                Modality.AUDIO,
            ],

            # Input audio:
            # PCM16 / 24kHz
            input_audio_format=InputAudioFormat.PCM16,

            # Output audio:
            # PCM16 / 24kHz
            output_audio_format=OutputAudioFormat.PCM16,

            # Voice Activity Detection
            turn_detection=AzureSemanticVadMultilingual(),

            # Echo cancellation
            input_audio_echo_cancellation=AudioEchoCancellation(),

            # Noise reduction
            input_audio_noise_reduction=AudioNoiseReduction(
                type="azure_deep_noise_suppression"
            ),
        )

        await self.connection.session.update(
            session=session_config
        )

        print("⚙️  Session configured")

    # ========================================================
    # Event processing
    # ========================================================

    async def process_events(self):
        """Listen for events coming from Voice Live."""

        async for event in self.connection:
            await self.handle_event(event)

    # ========================================================
    # Event handling
    # ========================================================

    async def handle_event(self, event):

        # ----------------------------------------------------
        # Session updated
        # ----------------------------------------------------

        if event.type == ServerEventType.SESSION_UPDATED:

            print("📡 Voice Live session ready")

            # Start microphone
            self.audio_processor.start_capture()

        # ----------------------------------------------------
        # User speech transcription
        # ----------------------------------------------------

        elif (
            event.type
            == ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED
        ):

            transcript = event.get("transcript", "")

            if transcript:
                print(f"👤 You: {transcript}")

        # ----------------------------------------------------
        # Agent speech transcription
        # ----------------------------------------------------

        elif event.type == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DONE:

            transcript = event.get("transcript", "")

            if transcript:
                print(f"🤖 Agent: {transcript}")

        # ----------------------------------------------------
        # User started speaking
        # ----------------------------------------------------

        elif (
            event.type
            == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED
        ):

            # Stop currently playing response
            self.audio_processor.clear_playback_queue()

            print("🎤 Listening...")

        # ----------------------------------------------------
        # User stopped speaking
        # ----------------------------------------------------

        elif (
            event.type
            == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED
        ):

            print("🤔 Thinking...")

        # ----------------------------------------------------
        # Agent audio chunk
        # ----------------------------------------------------

        elif event.type == ServerEventType.RESPONSE_AUDIO_DELTA:

            self.audio_processor.queue_audio(
                event.delta
            )

        # ----------------------------------------------------
        # Agent response completed
        # ----------------------------------------------------

        elif event.type == ServerEventType.RESPONSE_AUDIO_DONE:

            print("✓ Response complete\n")

        # ----------------------------------------------------
        # Error
        # ----------------------------------------------------

        elif event.type == ServerEventType.ERROR:

            print(
                f"❌ Voice Live error: "
                f"{event.error.message}"
            )


# ============================================================
# AudioProcessor
# ============================================================

class AudioProcessor:
    """
    Handles microphone input and speaker output using PyAudio.
    """

    def __init__(self, connection):

        self.connection = connection

        self.audio = pyaudio.PyAudio()

        # Audio configuration
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 24000

        # 1200 frames = 50 ms at 24kHz
        self.chunk_size = 1200

        # Streams
        self.input_stream = None
        self.output_stream = None

        # Queue for received audio
        self.playback_queue = queue.Queue()

        # Event loop
        self.loop = None

    # ========================================================
    # Microphone
    # ========================================================

    def start_capture(self):
        """Start microphone capture."""

        def capture_callback(
            in_data,
            frame_count,
            time_info,
            status,
        ):

            # Convert PCM bytes → Base64
            audio_base64 = base64.b64encode(
                in_data
            ).decode("utf-8")

            # Send audio asynchronously
            asyncio.run_coroutine_threadsafe(
                self.connection.input_audio_buffer.append(
                    audio=audio_base64
                ),
                self.loop,
            )

            return (
                None,
                pyaudio.paContinue,
            )

        # Get current asyncio event loop
        self.loop = asyncio.get_running_loop()

        self.input_stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            stream_callback=capture_callback,
        )

        print("🎤 Microphone started")

    # ========================================================
    # Speaker
    # ========================================================

    def start_playback(self):
        """Start speaker playback."""

        remaining = b""

        def playback_callback(
            in_data,
            frame_count,
            time_info,
            status,
        ):

            nonlocal remaining

            # Number of bytes needed
            bytes_needed = (
                frame_count
                * pyaudio.get_sample_size(
                    pyaudio.paInt16
                )
            )

            # Start with remaining audio
            output = remaining[:bytes_needed]

            remaining = remaining[bytes_needed:]

            # Get audio from queue
            while len(output) < bytes_needed:

                try:

                    audio_data = (
                        self.playback_queue.get_nowait()
                    )

                    # End signal
                    if audio_data is None:
                        break

                    output += audio_data

                except queue.Empty:

                    # Fill missing audio with silence
                    output += bytes(
                        bytes_needed - len(output)
                    )

                    break

            # Save extra bytes for next callback
            if len(output) > bytes_needed:

                remaining = output[bytes_needed:]

                output = output[:bytes_needed]

            return (
                output,
                pyaudio.paContinue,
            )

        self.output_stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            output=True,
            frames_per_buffer=self.chunk_size,
            stream_callback=playback_callback,
        )

        print("🔊 Speakers ready")

    # ========================================================
    # Queue audio
    # ========================================================

    def queue_audio(self, audio_data):
        """Add audio data directly to the playback queue."""
        self.playback_queue.put(audio_data)

    # ========================================================
    # Clear playback
    # ========================================================

    def clear_playback_queue(self):
        """Clear queued audio when user interrupts."""

        while not self.playback_queue.empty():

            try:

                self.playback_queue.get_nowait()

            except queue.Empty:

                break

    # ========================================================
    # Shutdown
    # ========================================================

    def shutdown(self):
        """Clean up audio resources."""

        try:

            if self.input_stream:

                self.input_stream.stop_stream()
                self.input_stream.close()

            if self.output_stream:

                self.playback_queue.put(None)

                self.output_stream.stop_stream()
                self.output_stream.close()

            self.audio.terminate()

            print("🔇 Audio stopped")

        except Exception as e:

            print(
                f"⚠️ Audio shutdown warning: {e}"
            )


# ============================================================
# Application entry point
# ============================================================

if __name__ == "__main__":
    main()
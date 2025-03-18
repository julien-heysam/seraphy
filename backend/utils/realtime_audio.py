# example requires websocket-client library:
# pip install websocket-client

import os
import json
import websocket
import threading
import time
import pyaudio
import base64
import queue
from datetime import datetime
from dotenv import load_dotenv
import random

# Load environment variables
load_dotenv(override=True)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

class AudioConfig:
    CHUNK_SIZE = 128  # Even smaller chunks for faster processing
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 24000  # Required sample rate for OpenAI
    AUDIO_BUFFER_SIZE = 128  # Smaller buffer for lower latency

class AudioManager:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.output_stream = None
        self.should_play_audio = True
        self.is_output_paused = False
        self.playback_thread = None
        self.playback_active = False
        self.playback_queue = queue.Queue(maxsize=10)  # Small queue for audio chunks
        self.debug_audio = True  # Enable detailed audio debugging
        
    def start_recording(self):
        if self.stream is not None:
            self.stop_recording()
            
        self.is_recording = True
        self.stream = self.audio.open(
            format=AudioConfig.FORMAT,
            channels=AudioConfig.CHANNELS,
            rate=AudioConfig.RATE,
            input=True,
            frames_per_buffer=AudioConfig.CHUNK_SIZE,
            stream_callback=self.audio_callback
        )
        print("🎤 Audio input stream started")
        
        self.initialize_output_stream()
        self.start_playback_thread()
        
    def initialize_output_stream(self):
        """Initialize the output stream for audio playback"""
        try:
            if self.output_stream:
                if self.output_stream.is_active():
                    self.output_stream.stop_stream()
                self.output_stream.close()
                self.output_stream = None
            
            default_output = self.audio.get_default_output_device_info()
            
            self.output_stream = self.audio.open(
                format=AudioConfig.FORMAT,
                channels=AudioConfig.CHANNELS,
                rate=AudioConfig.RATE,
                output=True,
                output_device_index=default_output['index'],
                frames_per_buffer=AudioConfig.CHUNK_SIZE,
                start=False
            )
            
            if self.output_stream:
                self.output_stream.start_stream()
                self.should_play_audio = True
                self.is_output_paused = False
                print("🔊 Audio output stream initialized")
        except Exception as e:
            print(f"❌ Error initializing output stream: {e}")
            self.output_stream = None
            
    def stop_recording(self):
        """Stop recording and cleanup resources"""
        self.is_recording = False
        
        if self.stream:
            try:
                if self.stream.is_active():
                    self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                print(f"Error stopping input stream: {e}")
            self.stream = None
            
        if self.output_stream:
            try:
                if self.output_stream.is_active():
                    self.output_stream.stop_stream()
                self.output_stream.close()
            except Exception as e:
                print(f"Error stopping output stream: {e}")
            self.output_stream = None
            
        self.stop_playback_thread()
        
    def cleanup(self):
        """Clean up all audio resources"""
        self.stop_recording()
        if self.audio:
            self.audio.terminate()
            self.audio = None

    def start_playback_thread(self):
        """Start a dedicated thread for audio playback"""
        self.playback_active = True
        self.playback_thread = threading.Thread(target=self._playback_worker)
        self.playback_thread.daemon = True
        self.playback_thread.start()
        print("🔊 Audio playback thread started")
        
    def stop_playback_thread(self):
        """Stop the playback thread"""
        self.playback_active = False
        # Clear the queue to unblock any waiting put() operations
        try:
            while not self.playback_queue.empty():
                self.playback_queue.get_nowait()
        except:
            pass
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=0.5)
        print("🔇 Audio playback thread stopped")
        
    def _playback_worker(self):
        """Worker function for the playback thread"""
        while self.playback_active:
            if not self.should_play_audio:
                with self.playback_queue.mutex:
                    self.playback_queue.queue.clear()
                time.sleep(0.01)
                continue
                
            if not self.output_stream or not self.output_stream.is_active():
                if self.debug_audio:
                    print("🔄 Reinitializing output stream...")
                self.initialize_output_stream()
                if not self.output_stream:
                    time.sleep(0.1)
                    continue
                
            try:
                audio_data = self.playback_queue.get(timeout=0.1)
                if isinstance(audio_data, bytes) and len(audio_data) > 0 and self.output_stream:
                    try:
                        self.output_stream.write(audio_data)
                        if self.debug_audio and random.random() < 0.05:
                            print(f"🔊 Playing audio chunk: {len(audio_data)} bytes")
                    except Exception as e:
                        print(f"❌ Error writing to audio stream: {e}")
                        self.initialize_output_stream()
            except queue.Empty:
                time.sleep(0.01)
            except Exception as e:
                print(f"❌ Error in playback thread: {e}")
                time.sleep(0.1)
    
    def play_audio(self, audio_data):
        """Queue audio data for playback"""
        if self.should_play_audio and len(audio_data) > 0:
            try:
                # Try to add to the queue without blocking
                # If the queue is full, we'll drop this chunk
                if not self.playback_queue.full():
                    self.playback_queue.put_nowait(audio_data)
                    if self.debug_audio and random.random() < 0.05:
                        print(f"📥 Queued audio chunk: {len(audio_data)} bytes")
                elif self.debug_audio and random.random() < 0.1:
                    print("⚠️ Audio queue full, dropping chunk")
            except Exception as e:
                print(f"❌ Error queuing audio: {e}")

    def stop_audio(self):
        """Stop audio playback immediately"""
        self.should_play_audio = False
        # Clear the playback queue
        try:
            while not self.playback_queue.empty():
                self.playback_queue.get_nowait()
        except:
            pass
        # Immediately stop the output stream
        if self.output_stream:
            try:
                self.output_stream.stop_stream()
                self.is_output_paused = True
                print("🔇 Audio output stopped")
            except Exception as e:
                print(f"❌ Error stopping audio stream: {e}")
                self.initialize_output_stream()

    def resume_audio(self):
        """Resume audio playback"""
        if self.is_output_paused:
            # Check if we need to reinitialize the output stream
            if not self.output_stream or not self.output_stream.is_active():
                self.initialize_output_stream()
            else:
                try:
                    self.output_stream.start_stream()
                except Exception as e:
                    print(f"❌ Error starting audio stream: {e}")
                    self.initialize_output_stream()
            
            self.should_play_audio = True
            self.is_output_paused = False
            print("▶️ Audio output resumed")

    def reset_output_stream(self):
        """Reset the output stream if there are issues"""
        try:
            if self.output_stream:
                self.output_stream.stop_stream()
                self.output_stream.close()
            self.output_stream = self.audio.open(
                format=AudioConfig.FORMAT,
                channels=AudioConfig.CHANNELS,
                rate=AudioConfig.RATE,
                output=True,
                frames_per_buffer=AudioConfig.CHUNK_SIZE
            )
            self.should_play_audio = True
            self.is_output_paused = False
        except Exception as e:
            print(f"\n❌ Error resetting audio stream: {e}")

    def audio_callback(self, in_data, frame_count, time_info, status):
        if self.is_recording:
            self.audio_queue.put(in_data)
            # Check for voice activity by looking at audio amplitude
            audio_data = bytes(in_data)
            # Convert bytes to 16-bit integers
            int_data = [int.from_bytes(audio_data[i:i+2], byteorder='little', signed=True) 
                       for i in range(0, len(audio_data), 2)]
            # Calculate RMS amplitude
            if int_data:
                rms = (sum(x*x for x in int_data) / len(int_data)) ** 0.5
                if rms > 500:  # Threshold for voice activity
                    self.stop_audio()  # Stop playback immediately when voice detected
        return (None, pyaudio.paContinue)

class ConversationManager:
    def __init__(self):
        self.url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
        self.headers = [
            f"Authorization: Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta: realtime=v1"
        ]
        self.ws = None
        self.conversation_active = True
        self.audio_manager = AudioManager()
        self.audio_buffer = bytearray()
        self.is_speaking = False
        self.is_assistant_speaking = False
        self.has_active_response = False
        self.last_chunk_time = time.time()
        self.speech_buffer = ""
        self.speech_start_time = None
        self.min_speech_duration = 0.5
        self.last_vad_event_time = 0
        self.vad_threshold = 0.1  # Adjusted back to a less sensitive threshold
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        self.debug_mode = True  # Enable debug mode to see more logs

    def on_open(self, ws):
        print("🟢 Connected to OpenAI realtime server.")
        
        init_event = {
            "type": "session.update",
            "session": {
                "instructions": (
                    "You are a helpful AI assistant. Be concise and clear in your responses. "
                    "When appropriate, use markdown formatting to structure your responses. "
                    "You are focused on clear and accurate responses in a professional style."
                ),
                "model": "gpt-4o-realtime-preview-2024-12-17",
                "modalities": ["text", "audio"],
                "temperature": 0.7,
                "max_response_output_tokens": 4096,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "voice": "sage",
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.2,  # Adjusted back to a less sensitive threshold
                    "prefix_padding_ms": 100,  # Adjusted for better balance
                    "silence_duration_ms": 400  # Adjusted for better balance
                }
            }
        }
        ws.send(json.dumps(init_event))
        
        self.audio_manager.start_recording()
        self.start_audio_sender()

    def start_audio_sender(self):
        def send_audio():
            while self.conversation_active:
                try:
                    if not self.audio_manager.audio_queue.empty():
                        audio_data = self.audio_manager.audio_queue.get()
                        # Convert to integers for amplitude check
                        int_data = [int.from_bytes(audio_data[i:i+2], byteorder='little', signed=True) 
                                  for i in range(0, len(audio_data), 2)]
                        # Calculate RMS amplitude
                        if int_data:
                            rms = (sum(x*x for x in int_data) / len(int_data)) ** 0.5
                            if rms > 500:  # Threshold for voice activity
                                self.stop_current_response(self.ws)
                        
                        # Send audio data for processing
                        encoded_audio = base64.b64encode(audio_data).decode('utf-8')
                        audio_event = {
                            "type": "input_audio_buffer.append",
                            "audio": encoded_audio
                        }
                        self.ws.send(json.dumps(audio_event))
                    else:
                        time.sleep(0.01)
                except Exception as e:
                    print(f"Error sending audio: {e}")
                    time.sleep(0.01)

        audio_thread = threading.Thread(target=send_audio)
        audio_thread.daemon = True
        audio_thread.start()

    def stop_current_response(self, ws):
        """Stop the current response immediately"""
        # First stop audio playback immediately
        self.audio_manager.stop_audio()
        self.audio_buffer.clear()
        
        # Then cancel the response on the server
        if self.has_active_response:
            try:
                event = {
                    "type": "response.cancel"
                }
                ws.send(json.dumps(event))
                print("\n🤚 Response cancelled")
            except Exception as e:
                print(f"\n❌ Error stopping response: {e}")
        
        self.is_assistant_speaking = False
        self.has_active_response = False

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            event_type = data.get("type", "")
            interim_text = data.get("text", "").strip()
            print(interim_text)
            
            if self.debug_mode:
                # Print event type for debugging
                if event_type not in ["input_audio_buffer.append"]:  # Skip noisy events
                    print(f"\n🔍 Event: {event_type}")
            
            if event_type == "session.created":
                print("\n🔵 Session created successfully - Ready to start conversation")
                print("\n👂 Waiting for your voice input...")
                self.reconnect_attempts = 0
                self.audio_manager.resume_audio()
            
            elif event_type == "speech.interim":
                # Show interim transcription while speaking
                interim_text = data.get("text", "").strip()
                if interim_text:
                    print(f"\r💭 You: {interim_text}", end="", flush=True)
            
            elif event_type == "response.create.success":
                self.has_active_response = True
                self.audio_manager.resume_audio()
                print("\n🎙️ Response created successfully")
            
            elif event_type == "response.text.delta":
                if not self.is_assistant_speaking:
                    print("\n🎯 Assistant started streaming response...")
                self.is_assistant_speaking = True
                self.has_active_response = True
                print(data.get("delta", ""), end="", flush=True)
            
            elif event_type == "response.audio.delta":
                self.is_assistant_speaking = True
                self.has_active_response = True
                
                # Debug output to verify we're receiving audio data
                audio_data = base64.b64decode(data["delta"])
                
                # Only log occasionally to avoid console spam
                if self.debug_mode and random.random() < 0.01:  # Log roughly 1% of chunks
                    print(f"\n🔊 Received audio chunk: {len(audio_data)} bytes")
                
                # Make sure audio playback is enabled
                if not self.audio_manager.should_play_audio:
                    self.audio_manager.resume_audio()
                
                # Queue the audio for playback
                self.audio_manager.play_audio(audio_data)
            
            elif event_type == "response.audio.done":
                self.is_assistant_speaking = False
                self.has_active_response = False
                print("\n📢 Assistant finished speaking")
                self.audio_buffer.clear()
                print("\n👂 Waiting for your voice input...")
                self.audio_manager.resume_audio()
            
            elif event_type == "response.text.done":
                self.is_assistant_speaking = False
                self.has_active_response = False
                print("\n✅ Text response complete")
            
            elif event_type == "input_audio_buffer.speech_started":
                current_time = time.time()
                time_since_last_vad = current_time - self.last_vad_event_time
                
                # More responsive speech detection
                if not self.is_speaking or time_since_last_vad > self.vad_threshold:
                    self.is_speaking = True
                    self.speech_start_time = current_time
                    print("\n🎤 Voice input detected - Started listening...")
                    
                    # Immediately stop the assistant from speaking when user starts speaking
                    if self.is_assistant_speaking or self.has_active_response:
                        print("\n🛑 User started speaking - Stopping assistant response")
                        self.audio_manager.stop_audio()
                        self.stop_current_response(ws)
                
                self.last_vad_event_time = current_time
            
            elif event_type == "input_audio_buffer.speech_ended":
                if self.is_speaking:
                    self.is_speaking = False
                    transcribed_text = data.get("text", "").strip()
                    
                    if transcribed_text:
                        print(f"\n✨ Final transcript: {transcribed_text}")
                        print("🎤 Voice input complete - Processing...")
                        event = {
                            "type": "conversation.item.create",
                            "item": {
                                "type": "user_message",
                                "text": transcribed_text
                            }
                        }
                        ws.send(json.dumps(event))
                        
                        print("\n⏳ Creating assistant response...")
                        time.sleep(0.5)
                        self.create_new_response(ws)
                    else:
                        print("\n🤫 Brief noise detected - Continuing to listen...")
                        self.audio_manager.resume_audio()
            
            elif event_type == "error":
                error_msg = data.get('error', {}).get('message', 'Unknown error')
                if "no active response found" not in error_msg.lower():
                    print(f"\n❌ Error: {error_msg}")
                
        except json.JSONDecodeError as e:
            print(f"\n❌ Error decoding message: {e}")
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            self.handle_connection_error(ws)

    def handle_connection_error(self, ws):
        """Handle WebSocket connection errors with retry logic"""
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            print(f"\n🔄 Attempting to reconnect... (Attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
            try:
                ws.close()
                time.sleep(2)  # Wait before reconnecting
                self.start_conversation()
            except Exception as e:
                print(f"\n❌ Reconnection failed: {e}")
        else:
            print("\n❌ Max reconnection attempts reached. Please restart the application.")

    def play_audio_buffer(self):
        if len(self.audio_buffer) > 0:
            print("\n🔉 Playing buffered audio...")
            self.audio_manager.play_audio(bytes(self.audio_buffer))
            self.audio_buffer.clear()

    def on_error(self, ws, error):
        print(f"\n❌ WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"\n🔴 WebSocket connection closed: {close_msg} (code: {close_status_code})")
        self.conversation_active = False
        self.audio_manager.cleanup()

    def create_new_response(self, ws):
        if not hasattr(self, '_last_response_time'):
            self._last_response_time = 0
        
        current_time = time.time()
        if current_time - self._last_response_time < 0.5:
            print("\n⏱️ Throttling response creation - too soon after last response")
            return
        
        # Reset response states before creating new one
        self.has_active_response = False
        self.is_assistant_speaking = False
        self.is_speaking = False  # Make sure we're not in speaking mode
        self.audio_manager.resume_audio()
            
        print("\n💭 Creating new response...")
        event = {
            "type": "response.create",
            "response": {
                "modalities": ["text", "audio"]
            }
        }
        try:
            ws.send(json.dumps(event))
            print("\n📤 Sent response.create event")
            self._last_response_time = current_time
        except Exception as e:
            print(f"\n❌ Error creating response: {e}")

    def send_user_message(self, ws, message):
        print("\n📤 Sending message to assistant...")
        event = {
            "type": "conversation.item.create",
            "item": {
                "type": "user_message",
                "text": message
            }
        }
        ws.send(json.dumps(event))
        self.create_new_response(ws)

    def handle_user_input(self, ws):
        try:
            print("\n👤 Your message (type 'quit' to exit):", end=" ")
            user_input = input().strip()
            
            if user_input.lower() == 'quit':
                print("👋 Ending conversation...")
                self.conversation_active = False
                ws.close()
                return
            
            if user_input:
                print("\n🤖 Assistant is thinking...")
                self.send_user_message(ws, user_input)
            else:
                self.handle_user_input(ws)
                
        except Exception as e:
            print(f"❌ Error handling user input: {e}")

    def start_conversation(self):
        websocket.enableTrace(False)
        self.ws = websocket.WebSocketApp(
            self.url,
            header=self.headers,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
        try:
            while self.conversation_active:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n👋 Gracefully shutting down...")
            self.conversation_active = False
            self.ws.close()
            self.audio_manager.cleanup()

def main():
    try:
        conversation = ConversationManager()
        conversation.start_conversation()
    except Exception as e:
        print(f"❌ Error in main: {e}")

if __name__ == "__main__":
    main()
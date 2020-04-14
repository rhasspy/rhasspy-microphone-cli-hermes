"""Hermes MQTT server for Rhasspy TTS using external program"""
import io
import logging
import re
import shlex
import socket
import subprocess
import threading
import time
import typing
import wave
from queue import Queue

import webrtcvad
from rhasspyhermes.asr import AsrStartListening, AsrStopListening
from rhasspyhermes.audioserver import (
    AudioDevice,
    AudioDeviceMode,
    AudioDevices,
    AudioFrame,
    AudioGetDevices,
    AudioRecordError,
    AudioSummary,
    SummaryToggleOff,
    SummaryToggleOn,
)
from rhasspyhermes.base import Message
from rhasspyhermes.client import GeneratorType, HermesClient

_LOGGER = logging.getLogger("rhasspymicrophone_cli_hermes")

# -----------------------------------------------------------------------------


class MicrophoneHermesMqtt(HermesClient):
    """Hermes MQTT server for Rhasspy microphone input using external program."""

    def __init__(
        self,
        client,
        record_command: typing.List[str],
        sample_rate: int,
        sample_width: int,
        channels: int,
        chunk_size: int = 2048,
        list_command: typing.Optional[typing.List[str]] = None,
        test_command: typing.Optional[str] = None,
        site_ids: typing.Optional[typing.List[str]] = None,
        output_site_id: typing.Optional[str] = None,
        udp_audio_host: str = "127.0.0.1",
        udp_audio_port: typing.Optional[int] = None,
        vad_mode: int = 3,
    ):
        super().__init__("rhasspymicrophone_cli_hermes", client, site_ids=site_ids)

        self.subscribe(AudioGetDevices, SummaryToggleOn, SummaryToggleOff)

        self.record_command = record_command
        self.sample_rate = sample_rate
        self.sample_width = sample_width
        self.channels = channels
        self.chunk_size = chunk_size
        self.list_command = list_command
        self.test_command = test_command

        self.output_site_id = output_site_id or self.site_id

        self.udp_audio_host = udp_audio_host
        self.udp_audio_port = udp_audio_port
        self.udp_output = False
        self.udp_socket: typing.Optional[socket.socket] = None

        self.chunk_queue: Queue = Queue()

        self.test_audio_buffer: typing.Optional[bytes] = None

        # Send audio summaries
        self.enable_summary = False
        self.vad: typing.Optional[webrtcvad.Vad] = None
        self.vad_mode = vad_mode
        self.vad_audio_data = bytes()
        self.vad_chunk_size: int = 960  # 30ms

        # Frames to skip between audio summaries
        self.summary_skip_frames = 5
        self.summary_frames_left = self.summary_skip_frames

        # Start threads
        if self.udp_audio_port is not None:
            self.udp_output = True
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            _LOGGER.debug(
                "Audio will also be sent to UDP %s:%s",
                self.udp_audio_host,
                self.udp_audio_port,
            )
            self.subscribe(AsrStartListening, AsrStopListening)

        threading.Thread(target=self.publish_chunks, daemon=True).start()
        threading.Thread(target=self.record, daemon=True).start()

    # -------------------------------------------------------------------------

    def record(self):
        """Record audio from external program's stdout."""
        try:
            _LOGGER.debug(self.record_command)
            record_proc = subprocess.Popen(self.record_command, stdout=subprocess.PIPE)
            _LOGGER.debug("Recording audio")

            while True:
                chunk = record_proc.stdout.read(self.chunk_size)
                if chunk:
                    self.chunk_queue.put(chunk)
                else:
                    # Avoid 100% CPU usage
                    time.sleep(0.01)
        except Exception as e:
            _LOGGER.exception("record")
            self.publish(
                AudioRecordError(
                    error=str(e),
                    context=str(self.record_command),
                    site_id=self.output_site_id,
                )
            )

    def publish_chunks(self):
        """Publish audio chunks to MQTT or UDP."""
        try:
            udp_dest = (self.udp_audio_host, self.udp_audio_port)

            while True:
                chunk = self.chunk_queue.get()
                if chunk:
                    if self.test_audio_buffer:
                        # Add to buffer for microphone test
                        self.test_audio_buffer += chunk

                    # MQTT output
                    with io.BytesIO() as wav_buffer:
                        wav_file: wave.Wave_write = wave.open(wav_buffer, "wb")
                        with wav_file:
                            wav_file.setframerate(self.sample_rate)
                            wav_file.setsampwidth(self.sample_width)
                            wav_file.setnchannels(self.channels)
                            wav_file.writeframes(chunk)

                        wav_bytes = wav_buffer.getvalue()

                        if self.udp_output:
                            # UDP output
                            self.udp_socket.sendto(wav_bytes, udp_dest)
                        else:
                            # Publish to output site_id
                            self.publish(
                                AudioFrame(wav_bytes=wav_bytes),
                                site_id=self.output_site_id,
                            )

                    if self.enable_summary:
                        self.summary_frames_left -= 1
                        if self.summary_frames_left > 0:
                            continue

                        self.summary_frames_left = self.summary_skip_frames
                        if not self.vad:
                            # Create voice activity detector
                            self.vad = webrtcvad.Vad()
                            self.vad.set_mode(self.vad_mode)

                        # webrtcvad needs 16-bit 16Khz mono
                        self.vad_audio_data += self.maybe_convert_wav(
                            wav_bytes, sample_rate=16000, sample_width=2, channels=1
                        )

                        is_speech = False

                        # Process in chunks of 30ms for webrtcvad
                        while len(self.vad_audio_data) >= self.vad_chunk_size:
                            vad_chunk = self.vad_audio_data[: self.vad_chunk_size]
                            self.vad_audio_data = self.vad_audio_data[
                                self.vad_chunk_size :
                            ]

                            # Speech in any chunk counts as speech
                            is_speech = is_speech or self.vad.is_speech(
                                vad_chunk, 16000
                            )

                        # Publish audio summary
                        self.publish(
                            AudioSummary(
                                debiased_energy=AudioSummary.get_debiased_energy(chunk),
                                is_speech=is_speech,
                            ),
                            site_id=self.output_site_id,
                        )
        except Exception as e:
            _LOGGER.exception("publish_chunks")
            self.publish(
                AudioRecordError(
                    error=str(e), context="publish_chunks", site_id=self.output_site_id
                )
            )

    # -------------------------------------------------------------------------

    async def handle_get_devices(
        self, get_devices: AudioGetDevices
    ) -> typing.AsyncIterable[typing.Union[AudioDevices, AudioRecordError]]:
        """Get available microphones and optionally test them."""

        if get_devices.modes and (AudioDeviceMode.INPUT not in get_devices.modes):
            _LOGGER.debug("Not a request for input devices")
            return

        devices: typing.List[AudioDevice] = []

        if self.list_command:
            try:
                # Run list command
                _LOGGER.debug(self.list_command)

                output = subprocess.check_output(
                    self.list_command, universal_newlines=True
                ).splitlines()

                # Parse output (assume like arecord -L)
                name, description = None, ""
                first_mic = True
                for line in output:
                    line = line.rstrip()
                    if re.match(r"^\s", line):
                        description = line.strip()
                        if first_mic:
                            description += "*"
                            first_mic = False
                    else:
                        if name is not None:
                            working = None
                            if get_devices.test:
                                working = self.get_microphone_working(name)

                            devices.append(
                                AudioDevice(
                                    mode=AudioDeviceMode.INPUT,
                                    id=name,
                                    name=name,
                                    description=description,
                                    working=working,
                                )
                            )

                        name = line.strip()
            except Exception as e:
                _LOGGER.exception("handle_get_devices")
                yield AudioRecordError(
                    error=str(e), context=get_devices.id, site_id=get_devices.site_id
                )
        else:
            _LOGGER.warning("No device list command. Cannot list microphones.")

        yield AudioDevices(
            devices=devices, id=get_devices.id, site_id=get_devices.site_id
        )

    def get_microphone_working(self, device_name: str, chunk_size: int = 1024) -> bool:
        """Record some audio from a microphone and check its energy."""
        try:
            # read audio
            assert self.test_command, "Test command is required"
            test_cmd = shlex.split(self.test_command.format(device_name))
            _LOGGER.debug(test_cmd)

            proc = subprocess.Popen(test_cmd, stdout=subprocess.PIPE)
            assert proc.stdout
            audio_data = proc.stdout.read(chunk_size * 2)
            proc.terminate()

            debiased_energy = AudioSummary.get_debiased_energy(audio_data)

            # probably actually audio
            return debiased_energy > 30
        except Exception:
            _LOGGER.exception("get_microphone_working ({device_name})")
            pass

        return False

    # -------------------------------------------------------------------------

    async def on_message_blocking(
        self,
        message: Message,
        site_id: typing.Optional[str] = None,
        session_id: typing.Optional[str] = None,
        topic: typing.Optional[str] = None,
    ) -> GeneratorType:
        """Received message from MQTT broker."""
        if isinstance(message, AudioGetDevices):
            async for device_result in self.handle_get_devices(message):
                yield device_result
        elif isinstance(message, AsrStartListening):
            if self.udp_audio_port is not None:
                self.udp_output = False
                _LOGGER.debug("Disable UDP output")
        elif isinstance(message, AsrStopListening):
            if self.udp_audio_port is not None:
                self.udp_output = True
                _LOGGER.debug("Enable UDP output")
        elif isinstance(message, SummaryToggleOn):
            self.enable_summary = True
            _LOGGER.debug("Enable audio summaries")
        elif isinstance(message, SummaryToggleOff):
            self.enable_summary = False
            _LOGGER.debug("Disable audio summaries")
        else:
            _LOGGER.warning("Unexpected message: %s", message)

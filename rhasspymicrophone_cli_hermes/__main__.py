"""Hermes MQTT service for Rhasspy TTS with external program."""
import argparse
import asyncio
import logging
import shlex

import paho.mqtt.client as mqtt
import rhasspyhermes.cli as hermes_cli

from . import MicrophoneHermesMqtt

_LOGGER = logging.getLogger("rhasspymicrophone_cli_hermes")

# -----------------------------------------------------------------------------


def main():
    """Main method."""
    parser = argparse.ArgumentParser(prog="rhasspy-microphone-cli-hermes")
    parser.add_argument(
        "--record-command", required=True, help="Command to record raw audio data"
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        required=True,
        help="Sample rate of recorded audio in hertz (e.g., 16000)",
    )
    parser.add_argument(
        "--sample-width",
        type=int,
        required=True,
        help="Sample width of recorded audio in bytes (e.g., 2)",
    )
    parser.add_argument(
        "--channels",
        type=int,
        required=True,
        help="Number of channels in recorded audio (e.g., 1)",
    )
    parser.add_argument("--list-command", help="Command to list available microphones")
    parser.add_argument("--test-command", help="Command to test a specific microphone")
    parser.add_argument(
        "--output-site-id", help="If set, output audio data to a different site_id"
    )
    parser.add_argument(
        "--udp-audio-host",
        default="127.0.0.1",
        help="Host for UDP audio (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--udp-audio-port",
        type=int,
        help="Send raw audio to UDP port outside ASR listening",
    )

    hermes_cli.add_hermes_args(parser)
    args = parser.parse_args()

    hermes_cli.setup_logging(args)
    _LOGGER.debug(args)

    if args.list_command:
        args.list_command = shlex.split(args.list_command)

    # Listen for messages
    client = mqtt.Client()
    hermes = MicrophoneHermesMqtt(
        client,
        shlex.split(args.record_command),
        args.sample_rate,
        args.sample_width,
        args.channels,
        list_command=args.list_command,
        test_command=args.test_command,
        site_ids=args.site_id,
        output_site_id=args.output_site_id,
        udp_audio_host=args.udp_audio_host,
        udp_audio_port=args.udp_audio_port,
    )

    _LOGGER.debug("Connecting to %s:%s", args.host, args.port)
    hermes_cli.connect(client, args)
    client.loop_start()

    try:
        # Run event loop
        asyncio.run(hermes.handle_messages_async())
    except KeyboardInterrupt:
        pass
    finally:
        _LOGGER.debug("Shutting down")
        client.loop_stop()


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()

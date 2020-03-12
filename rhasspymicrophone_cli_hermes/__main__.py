"""Hermes MQTT service for Rhasspy TTS with external program."""
import argparse
import logging
import shlex

import paho.mqtt.client as mqtt

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
        "--host", default="localhost", help="MQTT host (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=1883, help="MQTT port (default: 1883)"
    )
    parser.add_argument(
        "--siteId", default="default", help="Hermes siteId of this server"
    )
    parser.add_argument(
        "--output-siteId", help="If set, output audio data to a different siteId"
    )
    parser.add_argument(
        "--udp-audio-port",
        type=int,
        help="Send raw audio to UDP port outside ASR listening",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Print DEBUG messages to the console"
    )
    parser.add_argument(
        "--log-format",
        default="[%(levelname)s:%(asctime)s] %(name)s: %(message)s",
        help="Python logger format",
    )
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format=args.log_format)
    else:
        logging.basicConfig(level=logging.INFO, format=args.log_format)

    _LOGGER.debug(args)

    if args.list_command:
        args.list_command = shlex.split(args.list_command)

    try:
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
            siteId=args.siteId,
            output_siteId=args.output_siteId,
            udp_audio_port=args.udp_audio_port,
        )

        def on_disconnect(client, userdata, flags, rc):
            try:
                # Automatically reconnect
                _LOGGER.info("Disconnected. Trying to reconnect...")
                client.reconnect()
            except Exception:
                _LOGGER.exception("on_disconnect")

        # Connect
        client.on_connect = hermes.on_connect
        client.on_message = hermes.on_message
        client.on_disconnect = on_disconnect

        _LOGGER.debug("Connecting to %s:%s", args.host, args.port)
        client.connect(args.host, args.port)

        client.loop_forever()
    except KeyboardInterrupt:
        pass
    finally:
        _LOGGER.debug("Shutting down")


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()

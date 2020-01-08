#!/usr/bin/env bash

temp_wav="$(mktemp --suffix=.wav)"
function finish {
    rm -rf "${temp_wav}"
}

trap finish EXIT

pico2wave -w "${temp_wav}" "$@"
cat "${temp_wav}"

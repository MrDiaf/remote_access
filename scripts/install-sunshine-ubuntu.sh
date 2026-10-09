#!/usr/bin/env sh
# Installs the pinned official Sunshine release for this Ubuntu version.
# Run as root (make install-sunshine uses sudo). The package sets
# cap_sys_admin on /usr/bin/sunshine for KMS screen capture and installs udev
# rules for virtual keyboard, mouse and gamepads.
set -eu

SUNSHINE_VERSION=2026.914.233613

if [ "$(id -u)" -ne 0 ]; then
  printf "Run with sudo: make install-sunshine\n" >&2
  exit 1
fi

. /etc/os-release
case "${ID}:${VERSION_ID}" in
  ubuntu:22.04) sha=c7645396027b0601a09d49de89674b80b3c9ac7a3dffe0d52703738dab072f1c ;;
  ubuntu:24.04) sha=c38e9c705f650f8705f61702717e99bec34044c5028fcb8f23a08fe041292c21 ;;
  ubuntu:26.04) sha=b8a8ceeeb2b3f30a18a994ad268c94e0c91170f33a864c7aad31eed927ad7d47 ;;
  ubuntu:26.10) sha=1cedccbf3ce7836f1e83a74c23dd8dd7b49e2a0d341198f5b3ca47145244aedd ;;
  *)
    printf "No pinned Sunshine package for %s %s. See https://github.com/LizardByte/Sunshine/releases\n" "$ID" "$VERSION_ID" >&2
    exit 1
    ;;
esac

file="sunshine_${SUNSHINE_VERSION}-1+ubuntu${VERSION_ID}_amd64.deb"
url="https://github.com/LizardByte/Sunshine/releases/download/v${SUNSHINE_VERSION}/${file}"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

printf "Downloading %s\n" "$url"
curl -fSL -o "$tmp/$file" "$url"
printf "%s  %s\n" "$sha" "$tmp/$file" | sha256sum -c -

# apt runs as the _apt user, which must be able to read the file.
chmod 755 "$tmp"
chmod 644 "$tmp/$file"
apt-get install -y "$tmp/$file"

printf "\nSunshine %s installed.\n" "$SUNSHINE_VERSION"
printf "Remove it later with: sudo apt remove sunshine\n"

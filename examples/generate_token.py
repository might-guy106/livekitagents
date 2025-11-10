#!/usr/bin/env python3
"""
Generate a LiveKit token for testing the agent
"""

import os
import sys

# Load environment variables
from dotenv import load_dotenv

from livekit import api

load_dotenv()

# Get credentials from environment
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET")
LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "")

if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
    print("❌ Error: LIVEKIT_API_KEY and LIVEKIT_API_SECRET must be set in .env file")
    sys.exit(1)

# Get room name from command line or use default
room_name = sys.argv[1] if len(sys.argv) > 1 else "test-room"
participant_name = sys.argv[2] if len(sys.argv) > 2 else "user"

# Create token
token = (
    api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    .with_identity(participant_name)
    .with_name(participant_name)
    .with_grants(
        api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        )
    )
    .to_jwt()
)

# Extract domain from URL
domain = LIVEKIT_URL

print("\n" + "=" * 70)
print("✅ LiveKit Token Generated Successfully!")
print("=" * 70)
print(f"\nRoom: {room_name}")
print(f"Participant: {participant_name}")
print(f"Server: {domain}")
print(f"\n📋 Your Token:\n{token}")
print("\n" + "=" * 70)
print("\n🌐 Connect Options:")
print("\n1. Using LiveKit Meet:")
print(f"   Go to: https://meet.livekit.io/custom")
print(f"   - Server URL: {domain}")
print(f"   - Token: {token}")
print(f"   - Click Connect")
print("\n2. Using Browser Console (copy-paste this URL):")
print(f"   https://meet.livekit.io/custom?liveKitUrl={domain}&token={token}")
print("\n" + "=" * 70)

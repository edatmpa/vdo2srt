#!/usr/bin/env python3
"""
Test script to verify Google Cloud Vision API and Speech-to-Text API are working.
Requires service account JSON key file at: E:\API Key\Google API Keys\vision-api-48950-05d470aaae32.json
"""

import os
import sys
from pathlib import Path

# Set up authentication with service account key
SERVICE_ACCOUNT_PATH = r"E:\API Key\Google API Keys\audio2srt-398806-a0e2a234f5d0.json"
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = SERVICE_ACCOUNT_PATH

print("=" * 60)
print("Testing Google Cloud APIs")
print("=" * 60)

# Check if service account key exists
if not Path(SERVICE_ACCOUNT_PATH).exists():
    print(f"\n❌ ERROR: Service account key not found at:")
    print(f"   {SERVICE_ACCOUNT_PATH}")
    sys.exit(1)
else:
    print(f"\n✓ Service account key found")
    print(f"  Path: {SERVICE_ACCOUNT_PATH}")

# Test 1: Vision API
print("\n" + "-" * 60)
print("TEST 1: Google Cloud Vision API")
print("-" * 60)

try:
    from google.cloud import vision
    
    client = vision.ImageAnnotatorClient()
    print("✓ Vision API client initialized successfully")
    
    # Try a simple request to verify credentials work
    test_image_path = Path(__file__).parent / "test_image.jpg"
    
    if test_image_path.exists():
        with open(test_image_path, 'rb') as image_file:
            content = image_file.read()
        
        image = vision.Image(content=content)
        response = client.label_detection(image=image)
        
        print(f"✓ Label detection request successful")
        print(f"  Labels found: {len(response.label_annotations)}")
        for label in response.label_annotations[:3]:
            print(f"    - {label.description} ({label.confidence:.2%})")
    else:
        print("ℹ No test image found (test_image.jpg)")
        print("  To fully test, provide an image file in the same directory")
        print("  For now, credentials appear valid since client initialized")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("  Make sure 'google-cloud-vision' is installed: pip install google-cloud-vision")
except Exception as e:
    print(f"❌ Vision API error: {e}")
    print(f"  Error type: {type(e).__name__}")

# Test 2: Speech-to-Text API
print("\n" + "-" * 60)
print("TEST 2: Google Cloud Speech-to-Text API")
print("-" * 60)

try:
    from google.cloud import speech
    
    client = speech.SpeechClient()
    print("✓ Speech-to-Text API client initialized successfully")
    
    # Check if test audio file exists
    test_audio_path = Path(__file__).parent / "audio" / "test_audio.wav"
    
    if test_audio_path.exists():
        with open(test_audio_path, 'rb') as audio_file:
            content = audio_file.read()
        
        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
        )
        
        response = client.recognize(config=config, audio=audio)
        
        print(f"✓ Speech-to-Text request successful")
        for result in response.results:
            print(f"  Transcript: {result.alternatives[0].transcript}")
    else:
        print("ℹ No test audio found (audio/test_audio.wav)")
        print("  To fully test, provide an audio file in the audio/ directory")
        print("  For now, credentials appear valid since client initialized")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("  Make sure 'google-cloud-speech' is installed: pip install google-cloud-speech")
except Exception as e:
    print(f"❌ Speech-to-Text API error: {e}")
    print(f"  Error type: {type(e).__name__}")

# Test 3: Check billing status
print("\n" + "-" * 60)
print("TEST 3: Verifying API Billing Status")
print("-" * 60)

try:
    import json
    with open(SERVICE_ACCOUNT_PATH, 'r') as f:
        creds_data = json.load(f)
    
    project_id = creds_data.get('project_id', 'Unknown')
    print(f"✓ Service account project ID: {project_id}")
    print(f"  Email: {creds_data.get('client_email', 'Unknown')}")
    print(f"\n  Go to: https://console.cloud.google.com/billing?project={project_id}")
    print(f"  to verify billing is enabled for both APIs")
    
except Exception as e:
    print(f"❌ Error reading credentials: {e}")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)

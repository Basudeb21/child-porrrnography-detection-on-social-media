def send_to_moderation_api(image_path: str, minor_detected: bool, nsfw_scores: dict, is_blur_applied: bool = True):
    """
    Send detection results to moderation API to UPDATE existing record
    """
    filename = os.path.basename(image_path)
    
    payload = {
        "filename": filename,
        "minor_detected": minor_detected,
        "nsfw_scores": nsfw_scores,
        "is_blur_applied": is_blur_applied
    }
    
    print(f"📤 Sending moderation data for: {filename}")
    print(f"   - Minor detected: {minor_detected}")
    print(f"   - NSFW scores: {nsfw_scores}")
    print(f"   - Blur applied: {is_blur_applied}")
    
    last_err = None
    for attempt in range(3):
        try:
            response = requests.post(
                f"{MODERATION_API_BASE}/moderation/process",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Successfully UPDATED database record:")
                print(f"   - File: {result.get('filename')}")
                print(f"   - Minor: {result.get('minor_detected')}")
                print(f"   - NSFW: {result.get('nsfw_detected')}")
                print(f"   - Flagged: {result.get('flagged_by_ai')}")
                print(f"   - Reported: {result.get('is_reported')}")
                print(f"   - Status: {result.get('report_status')}")
                return True
            else:
                print(f"❌ API Error ({response.status_code}): {response.text}")
                last_err = response.text
                
        except Exception as e:
            print(f"❌ Request failed: {e}")
            last_err = str(e)
        
        time.sleep(2)  # Wait before retry
    
    print(f"❌ Failed to update after 3 attempts. Last error: {last_err}")
    return False

# Update the process_image function
def process_image(self, image_path: str):
    print(f"🔍 Processing image: {os.path.basename(image_path)}")

    try:
        # Run NSFW detection
        result = self.detector.predict(image_path, THRESHOLD)

        if result.get('error'):
            print(f"❌ Detection error: {result['error']}")
            return

        scores = result.get("scores", {})
        porn_pct = scores.get("porn", 0)
        hentai_pct = scores.get("hentai", 0)
        sexy_pct = scores.get("sexy", 0)
        
        # Determine if blur should be applied (your NSFW threshold)
        is_blur_applied = porn_pct > 80.0 or hentai_pct > 80.0 or sexy_pct > 70.0
        
        print(f"📊 NSFW Scores - Porn: {porn_pct}%, Hentai: {hentai_pct}%, Sexy: {sexy_pct}%")
        print(f"🎭 Minor detected: True")  # Since this runs in minor folder
        print(f"🔞 NSFW detected: {is_blur_applied}")
        print(f"🔄 Blur applied: {is_blur_applied}")

        # Send to moderation API to UPDATE existing record
        success = send_to_moderation_api(
            image_path=image_path,
            minor_detected=True,  # Always true since we're in minor folder
            nsfw_scores=scores,
            is_blur_applied=is_blur_applied
        )

        if success:
            print("✅ Successfully UPDATED database record")
        else:
            print("❌ Failed to update database record")

    except Exception as e:
        print(f"❌ Processing failed: {str(e)}")

    finally:
        # Clean up the processed image
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
                print(f"🗑️ Deleted processed image: {image_path}")
        except Exception as e:
            print(f"❌ Failed to delete image {image_path}: {e}")
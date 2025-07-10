#!/usr/bin/env python3
"""
Test avec votre ancien style de configuration qui donnait les bonnes couleurs
Utilise les contrôles libcamera directement dans la configuration
"""

import cv2
import time
import asyncio
from picamera2 import Picamera2
from libcamera import controls

def test_with_old_style_config():
    """Test avec votre configuration qui fonctionnait"""
    print("🎨 Test avec votre ancien style de configuration...")
    
    picam2 = Picamera2()
    
    try:
        # Configuration prévisualisation EXACTEMENT comme votre ancien code
        preview_config = picam2.create_preview_configuration(
            main={"size": (1280, 720)},
            controls={
                "AfMode": controls.AfModeEnum.Continuous,
                "AfSpeed": controls.AfSpeedEnum.Fast
            }
        )
        
        # Configuration photo EXACTEMENT comme votre ancien code
        still_config = picam2.create_still_configuration(
            main={"size": (4624, 3472)},
            controls={"AfMode": controls.AfModeEnum.Manual}
        )
        
        print("✅ Configurations créées avec contrôles libcamera intégrés")
        
        # Test 1: Preview avec votre ancienne méthode
        print("\n1. Test preview (ancien style)...")
        picam2.configure(preview_config)
        picam2.start()
        time.sleep(3)  # Laisser le temps à l'AF de se stabiliser
        
        # Capture du preview
        frame = picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imwrite("test_old_preview.jpg", frame_bgr)
        print("   Sauvé: test_old_preview.jpg")
        
        # Test 2: Photo avec votre ancienne méthode
        print("\n2. Test photo (ancien style)...")
        picam2.stop()
        picam2.configure(still_config)
        picam2.start()
        time.sleep(0.5)
        
        # Capture photo
        frame_still = picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame_still, cv2.COLOR_RGB2BGR)
        cv2.imwrite("test_old_still.jpg", frame_bgr)
        print("   Sauvé: test_old_still.jpg")
        
        # Retour au preview
        picam2.stop()
        picam2.configure(preview_config)
        picam2.start()
        time.sleep(1)
        
        print("\n✅ Test terminé avec votre ancien style")
        print("   Ces images devraient avoir les bonnes couleurs!")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
    finally:
        picam2.stop()
        picam2.close()

def test_streaming_like_old_code():
    """Test du streaming comme votre ancien get_video_stream"""
    print("\n📹 Test streaming style ancien code...")
    
    picam2 = Picamera2()
    
    try:
        # Configuration exacte de votre ancien code
        preview_config = picam2.create_preview_configuration(
            main={"size": (1280, 720)},
            controls={
                "AfMode": controls.AfModeEnum.Continuous,
                "AfSpeed": controls.AfSpeedEnum.Fast
            }
        )
        
        picam2.configure(preview_config)
        picam2.start()
        time.sleep(2)
        
        print("   Capture de 5 frames comme dans votre ancien streaming...")
        
        for i in range(5):
            # Capture et encodage comme votre ancien code
            array = picam2.capture_array()
            frame = cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
            
            filename = f"streaming_frame_{i+1}.jpg"
            cv2.imwrite(filename, frame)
            print(f"   Frame {i+1} sauvé: {filename}")
            
            time.sleep(0.5)
        
        print("✅ Test streaming terminé")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
    finally:
        picam2.stop()
        picam2.close()

def test_focus_and_capture_sequence():
    """Test de la séquence focus + capture comme votre ancien code"""
    print("\n🔍 Test séquence focus + capture (ancien style)...")
    
    picam2 = Picamera2()
    
    try:
        # Configuration preview
        preview_config = picam2.create_preview_configuration(
            main={"size": (1280, 720)},
            controls={
                "AfMode": controls.AfModeEnum.Continuous,
                "AfSpeed": controls.AfSpeedEnum.Fast
            }
        )
        
        # Configuration still
        still_config = picam2.create_still_configuration(
            main={"size": (4624, 3472)},
            controls={"AfMode": controls.AfModeEnum.Manual}
        )
        
        # Phase 1: Focus en mode preview
        print("   Phase 1: Autofocus en mode preview...")
        picam2.configure(preview_config)
        picam2.set_controls({
            "AfMode": controls.AfModeEnum.Continuous,
            "AfSpeed": controls.AfSpeedEnum.Fast
        })
        picam2.start()
        
        # Attendre focus comme votre ancien code
        start_time = time.time()
        focused = False
        
        while time.time() - start_time < 8:
            metadata = picam2.capture_metadata()
            state = metadata.get("AfState")
            print(f"      AfState = {state}")
            if state == 2:  # focused
                focused = True
                break
            elif state == 3:  # failed
                break
            time.sleep(0.1)
        
        # Capturer position focus
        lens_pos = metadata.get("LensPosition")
        print(f"   Position focus capturée: {lens_pos}")
        
        # Phase 2: Capture en mode still
        print("   Phase 2: Capture en mode still...")
        picam2.stop()
        picam2.configure(still_config)
        picam2.start()
        time.sleep(0.5)
        
        # Capture
        array = picam2.capture_array()
        frame = cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
        cv2.imwrite("test_focus_capture.jpg", frame)
        print("   Sauvé: test_focus_capture.jpg")
        
        # Phase 3: Retour preview
        print("   Phase 3: Retour preview...")
        picam2.stop()
        picam2.configure(preview_config)
        picam2.start()
        
        print("✅ Séquence complète terminée")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
    finally:
        picam2.stop()
        picam2.close()

def main():
    print("🎨 TEST AVEC VOTRE ANCIEN STYLE QUI MARCHAIT")
    print("============================================")
    print("Reproduction exacte de votre ancien code qui donnait les bonnes couleurs")
    
    try:
        test_with_old_style_config()
        test_streaming_like_old_code()
        test_focus_and_capture_sequence()
        
        print("\n✅ TOUS LES TESTS TERMINÉS")
        print("==========================")
        print("📁 Images générées:")
        print("  - test_old_preview.jpg (preview ancien style)")
        print("  - test_old_still.jpg (photo ancien style)")
        print("  - streaming_frame_*.jpg (frames streaming)")
        print("  - test_focus_capture.jpg (séquence complète)")
        print("")
        print("🔍 Ces images devraient avoir les BONNES couleurs")
        print("   Si c'est le cas, je vais adapter le code principal!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Arrêt demandé")
    except Exception as e:
        print(f"\n❌ Erreur globale: {e}")

if __name__ == "__main__":
    main()
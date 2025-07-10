#!/usr/bin/env python3
"""
Test de détection des labels blancs
Pour vérifier que la détection fonctionne correctement avant le décodage DataMatrix
"""

import cv2
import numpy as np
import os
from pathlib import Path

def extract_white_label_test(gray_image, debug_name="test"):
    """Version test de la fonction d'extraction avec debug visuel"""
    try:
        print(f"  Analyse de l'image {debug_name}...")
        print(f"    Taille: {gray_image.shape}")
        print(f"    Luminosité moyenne: {np.mean(gray_image):.1f}")
        
        # Seuillage pour isoler les zones blanches (plus strict)
        _, thresh = cv2.threshold(gray_image, 220, 255, cv2.THRESH_BINARY)
        cv2.imwrite(f"debug_{debug_name}_01_threshold.jpg", thresh)
        
        white_pixels = np.sum(thresh == 255)
        total_pixels = thresh.shape[0] * thresh.shape[1]
        white_ratio_global = white_pixels / total_pixels
        print(f"    Ratio pixels blancs global: {white_ratio_global:.3f}")
        
        # Morphologie pour nettoyer
        kernel = np.ones((3, 3), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
        cv2.imwrite(f"debug_{debug_name}_02_morphology.jpg", cleaned)
        
        # Détection des contours
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Image de debug pour les contours
        contour_img = cv2.cvtColor(gray_image, cv2.COLOR_GRAY2BGR)
        cv2.drawContours(contour_img, contours, -1, (0, 255, 0), 2)
        cv2.imwrite(f"debug_{debug_name}_03_contours.jpg", contour_img)
        
        print(f"    Contours trouvés: {len(contours)}")
        
        if not contours:
            print("    ❌ Aucun contour trouvé")
            return None
        
        # Analyse de chaque contour
        candidates = []
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            
            # Filtre sur la taille
            if area < 2000 or area > gray_image.shape[0] * gray_image.shape[1] * 0.3:
                continue
            
            # Approximation du contour
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Vérification rectangulaire
            if len(approx) < 4 or len(approx) > 8:
                continue
            
            # Ratio largeur/hauteur
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = max(w, h) / min(w, h)
            
            if aspect_ratio > 4:
                continue
            
            # Score
            rectangularity = len(approx) / 4.0
            score = area * (2 - abs(rectangularity - 1))
            
            candidates.append({
                'contour': contour,
                'area': area,
                'bbox': (x, y, w, h),
                'approx_points': len(approx),
                'aspect_ratio': aspect_ratio,
                'score': score
            })
            
            print(f"    Candidat {i}: aire={area:.0f}, bbox={w}x{h}, points={len(approx)}, ratio={aspect_ratio:.2f}, score={score:.0f}")
        
        if not candidates:
            print("    ❌ Aucun candidat valide")
            return None
        
        # Sélection du meilleur candidat
        best_candidate = max(candidates, key=lambda c: c['score'])
        x, y, w, h = best_candidate['bbox']
        
        print(f"    ✅ Meilleur candidat sélectionné: {w}x{h}, score={best_candidate['score']:.0f}")
        
        # Extraction avec marge
        margin = min(10, w//10, h//10)
        x_extract = max(0, x - margin)
        y_extract = max(0, y - margin)
        w_extract = min(gray_image.shape[1] - x_extract, w + 2 * margin)
        h_extract = min(gray_image.shape[0] - y_extract, h + 2 * margin)
        
        extracted_label = gray_image[y_extract:y_extract+h_extract, x_extract:x_extract+w_extract]
        
        # Vérification finale du ratio de blanc
        white_ratio = np.sum(extracted_label > 200) / (w_extract * h_extract)
        print(f"    Ratio blanc dans le label: {white_ratio:.3f}")
        
        if white_ratio < 0.3:
            print("    ❌ Label trop sombre")
            return None
        
        # Sauvegarde du label extrait
        cv2.imwrite(f"debug_{debug_name}_04_extracted_label.jpg", extracted_label)
        
        # Image avec le rectangle de sélection
        result_img = cv2.cvtColor(gray_image, cv2.COLOR_GRAY2BGR)
        cv2.rectangle(result_img, (x_extract, y_extract), (x_extract + w_extract, y_extract + h_extract), (0, 255, 0), 3)
        cv2.putText(result_img, f"Label {w_extract}x{h_extract}", (x_extract, y_extract-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imwrite(f"debug_{debug_name}_05_result.jpg", result_img)
        
        print(f"    ✅ Label extrait avec succès: {w_extract}x{h_extract}")
        return extracted_label
        
    except Exception as e:
        print(f"    ❌ Erreur: {e}")
        return None

def test_on_captured_images():
    """Test sur les images capturées existantes"""
    print("🔍 Test sur les images capturées...")
    
    images_dir = Path("images")
    if not images_dir.exists():
        print("❌ Dossier images non trouvé")
        return
    
    image_files = list(images_dir.glob("*.jpg"))
    # Exclure les fichiers debug
    image_files = [f for f in image_files if "_debug" not in f.name]
    
    if not image_files:
        print("❌ Aucune image trouvée dans le dossier images")
        return
    
    # Tester les 3 dernières images
    recent_images = sorted(image_files, key=lambda x: x.stat().st_mtime, reverse=True)[:3]
    
    for image_path in recent_images:
        print(f"\n📸 Test sur: {image_path.name}")
        
        try:
            # Chargement
            image = cv2.imread(str(image_path))
            if image is None:
                print("  ❌ Impossible de charger l'image")
                continue
            
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Test d'extraction
            debug_name = image_path.stem
            label = extract_white_label_test(gray, debug_name)
            
            if label is not None:
                print(f"  ✅ Label détecté avec succès")
            else:
                print(f"  ❌ Aucun label détecté")
                
        except Exception as e:
            print(f"  ❌ Erreur: {e}")

def test_on_synthetic_image():
    """Test sur une image synthétique avec label blanc"""
    print("\n🎨 Test sur image synthétique...")
    
    # Création d'une image de test
    img = np.zeros((800, 1200), dtype=np.uint8)
    img.fill(100)  # Fond gris
    
    # Ajout d'un "PCB" vert
    cv2.rectangle(img, (200, 150), (1000, 650), 120, -1)
    
    # Ajout d'un label blanc avec DataMatrix simulé
    label_x, label_y = 400, 300
    label_w, label_h = 200, 100
    
    # Label blanc
    cv2.rectangle(img, (label_x, label_y), (label_x + label_w, label_y + label_h), 250, -1)
    
    # Bordure du label
    cv2.rectangle(img, (label_x, label_y), (label_x + label_w, label_y + label_h), 200, 2)
    
    # Simulation d'un DataMatrix (grille de points)
    matrix_start_x = label_x + 20
    matrix_start_y = label_y + 20
    matrix_size = 60
    
    for i in range(8):
        for j in range(8):
            if (i + j) % 2 == 0:  # Pattern en damier
                cv2.rectangle(img, 
                    (matrix_start_x + i*7, matrix_start_y + j*7),
                    (matrix_start_x + i*7 + 5, matrix_start_y + j*7 + 5),
                    50, -1)
    
    # Ajout de texte sur le label
    cv2.putText(img, "AE-F22050360-00B", (label_x + 80, label_y + 80), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, 100, 1)
    
    # Sauvegarde de l'image de test
    cv2.imwrite("debug_synthetic_input.jpg", img)
    print("  Image synthétique créée: debug_synthetic_input.jpg")
    
    # Test d'extraction
    label = extract_white_label_test(img, "synthetic")
    
    if label is not None:
        print("  ✅ Test synthétique réussi")
    else:
        print("  ❌ Test synthétique échoué")

def main():
    print("🏷️  TEST DE DÉTECTION DES LABELS BLANCS")
    print("=======================================")
    
    try:
        test_on_synthetic_image()
        test_on_captured_images()
        
        print("\n✅ TESTS TERMINÉS")
        print("=================")
        print("📁 Fichiers de debug générés:")
        print("  - debug_*_01_threshold.jpg (seuillage)")
        print("  - debug_*_02_morphology.jpg (nettoyage)")
        print("  - debug_*_03_contours.jpg (contours détectés)")
        print("  - debug_*_04_extracted_label.jpg (label extrait)")
        print("  - debug_*_05_result.jpg (résultat final)")
        print("")
        print("🔍 Instructions:")
        print("1. Vérifiez les fichiers de debug")
        print("2. Les images _05_result.jpg montrent les labels détectés")
        print("3. Si aucun label n'est détecté, vérifiez l'éclairage et le contraste")
        
    except KeyboardInterrupt:
        print("\n⏹️ Arrêt demandé")
    except Exception as e:
        print(f"\n❌ Erreur globale: {e}")

if __name__ == "__main__":
    main()
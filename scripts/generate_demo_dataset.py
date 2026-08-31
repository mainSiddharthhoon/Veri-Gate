import os
import shutil
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random

def create_dirs():
    dirs = [
        "demo_data/valid",
        "demo_data/mismatch",
        "demo_data/tampered",
        "demo_data/invalid"
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)

def generate_passport(face_path, output_path, tampered=False):
    # Create base image
    img = Image.new('RGB', (800, 550), color=(245, 245, 245))
    draw = ImageDraw.Draw(img)
    
    # Try to load a font, fallback to default
    try:
        font_large = ImageFont.truetype("arial.ttf", 24)
        font_small = ImageFont.truetype("arial.ttf", 16)
        font_mrz = ImageFont.truetype("cour.ttf", 26)
    except IOError:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_mrz = ImageFont.load_default()

    # Draw headers
    draw.text((350, 20), "PASSPORT / PASSEPORT", fill=(50, 50, 150), font=font_large)
    
    # Paste face
    try:
        face = Image.open(face_path)
        face = face.resize((200, 250))
        img.paste(face, (60, 200))
    except Exception as e:
        print(f"Could not load face {face_path}: {e}")
        # Draw placeholder
        draw.rectangle([60, 200, 260, 450], fill=(200, 200, 200))
        
    # Draw Fields
    fields = [
        ("Type", "P", 300, 80),
        ("Country Code", "GBR", 450, 80),
        ("Passport No.", "AB1234567", 600, 80),
        ("Surname", "SMITH", 300, 140),
        ("Given Names", "JAMES EDWARD", 300, 200),
        ("Nationality", "BRITISH", 300, 260),
        ("Date of Birth", "15 MAR / MAR 1985", 300, 320),
        ("Sex", "M", 600, 320),
        ("Date of Issue", "20 JUL / JUL 2019", 300, 380),
        ("Date of Expiry", "20 JUL / JUL 2029", 600, 380)
    ]
    
    for label, value, x, y in fields:
        draw.text((x, y), label, fill=(100, 100, 100), font=font_small)
        draw.text((x, y + 20), value, fill=(0, 0, 0), font=font_large)
        
    # Draw MRZ - ensuring no overlap with face
    mrz1 = "P<GBRSMITH<<JAMES<EDWARD<<<<<<<<<<<<<<<<<<<<"
    mrz2 = "AB12345671GBR8503150M2907206<<<<<<<<<<<<<<04"
    draw.text((40, 470), mrz1, fill=(0, 0, 0), font=font_mrz)
    draw.text((40, 500), mrz2, fill=(0, 0, 0), font=font_mrz)
    
    # Add tampering if requested
    if tampered:
        # Simulate tampering by pasting a slightly different quality/noisy box over the Surname
        tamper_box = img.crop((295, 135, 450, 190))
        # Add slight noise and jpeg compression artifacts
        tamper_box = tamper_box.filter(ImageFilter.GaussianBlur(0.5))
        # Save and reload to introduce JPEG artifacts
        tamper_box.save("temp_tamper.jpg", "JPEG", quality=30)
        tamper_box = Image.open("temp_tamper.jpg")
        img.paste(tamper_box, (295, 135))
        os.remove("temp_tamper.jpg")

    img.save(output_path, "JPEG", quality=95)

def create_invalid_image(output_path):
    img = Image.new('RGB', (800, 500), color=(150, 50, 50))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 60)
    except IOError:
        font = ImageFont.load_default()
    draw.text((100, 200), "NOT A DOCUMENT", fill=(255, 255, 255), font=font)
    img.save(output_path, "JPEG", quality=90)
    
def copy_face(src, dest):
    face = Image.open(src)
    face.save(dest, "JPEG", quality=95)

def main():
    matching_face_src = r"C:\Users\Arvindbhai\.gemini\antigravity-ide\brain\c83dd204-0809-4fd9-8780-d7dc014e7a61\matching_face_1788091869781.jpg"
    different_face_src = r"C:\Users\Arvindbhai\.gemini\antigravity-ide\brain\c83dd204-0809-4fd9-8780-d7dc014e7a61\different_face_1788091889808.jpg"
    
    create_dirs()
    
    print("Generating Valid Case...")
    generate_passport(matching_face_src, "demo_data/valid/document.jpg")
    copy_face(matching_face_src, "demo_data/valid/matching_face.jpg")
    
    print("Generating Mismatch Case...")
    generate_passport(matching_face_src, "demo_data/mismatch/document.jpg")
    copy_face(different_face_src, "demo_data/mismatch/different_face.jpg")
    
    print("Generating Tampered Case...")
    generate_passport(matching_face_src, "demo_data/tampered/document.jpg", tampered=True)
    copy_face(matching_face_src, "demo_data/tampered/matching_face.jpg")
    
    print("Generating Invalid Case...")
    create_invalid_image("demo_data/invalid/invalid_document.jpg")
    create_invalid_image("demo_data/invalid/invalid_face.jpg")

    print("Done!")

if __name__ == '__main__':
    main()

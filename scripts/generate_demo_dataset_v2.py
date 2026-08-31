import os
import shutil
from PIL import Image, ImageDraw, ImageFont, ImageFilter

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
    # Canvas: 800x600 to give plenty of room for MRZ
    img = Image.new('RGB', (800, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    try:
        font_large = ImageFont.truetype("arial.ttf", 26)
        font_small = ImageFont.truetype("arial.ttf", 14)
        font_mrz = ImageFont.truetype("cour.ttf", 26)
        font_watermark = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_mrz = ImageFont.load_default()
        font_watermark = ImageFont.load_default()

    # Draw header and WATERMARK
    draw.text((300, 20), "PASSPORT / PASSEPORT", fill=(50, 50, 150), font=font_large)
    draw.text((250, 250), "DEMO / SYNTHETIC", fill=(220, 220, 220), font=font_watermark)
    
    # Paste face (Left side, from y=80 to y=330. Width=200, height=250)
    try:
        face = Image.open(face_path)
        face = face.resize((200, 250))
        img.paste(face, (40, 80))
    except Exception as e:
        print(f"Could not load face {face_path}: {e}")
        draw.rectangle([40, 80, 240, 330], fill=(200, 200, 200))
        
    # Draw Fields (Right side, starting x=280)
    fields = [
        ("Type", "P", 280, 80),
        ("Country Code", "GBR", 420, 80),
        ("Passport No.", "AB1234567", 560, 80),
        ("Surname", "SMITH", 280, 140),
        ("Given Names", "JAMES EDWARD", 280, 200),
        ("Nationality", "BRITISH", 280, 260),
        ("Date of Birth", "15 MAR / MAR 1985", 280, 320),
        ("Sex", "M", 560, 320),
        ("Date of Issue", "20 JUL / JUL 2019", 280, 380),
        ("Date of Expiry", "20 JUL / JUL 2029", 560, 380)
    ]
    
    for label, value, x, y in fields:
        draw.text((x, y), label, fill=(100, 100, 100), font=font_small)
        draw.text((x, y + 20), value, fill=(0, 0, 0), font=font_large)
        
    # Draw MRZ (Bottom, starting y=480, completely separate from face which ends at 330)
    # Line 1: 44 chars
    mrz1 = "P<GBRSMITH<<JAMES<EDWARD<<<<<<<<<<<<<<<<<<<<"
    # Line 2: 44 chars
    mrz2 = "AB12345671GBR8503150M2907206<<<<<<<<<<<<<<04"
    draw.text((30, 480), mrz1, fill=(0, 0, 0), font=font_mrz)
    draw.text((30, 520), mrz2, fill=(0, 0, 0), font=font_mrz)
    
    if tampered:
        # Simulate tampering by drawing a solid red rectangle over the face
        # This triggers Face Region ELA (0.5) and EXIF (0.2) and Face Mismatch (critical).
        draw.rectangle((40, 80, 100, 120), fill=(255, 0, 0))
        
        # Add EXIF tag to reliably trigger metadata tampering detection
        exif = img.getexif()
        exif[305] = "Adobe Photoshop 2024"
        img.save(output_path, "JPEG", quality=95, exif=exif)
    else:
        img.save(output_path, "JPEG", quality=95)

def create_invalid_image(output_path, text="NOT A DOCUMENT"):
    img = Image.new('RGB', (800, 600), color=(150, 50, 50))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 60)
    except IOError:
        font = ImageFont.load_default()
    draw.text((100, 250), text, fill=(255, 255, 255), font=font)
    img.save(output_path, "JPEG", quality=90)
    
def copy_file(src, dest):
    shutil.copyfile(src, dest)

def main():
    matching_face_src = r"C:\Users\Arvindbhai\.gemini\antigravity-ide\brain\c83dd204-0809-4fd9-8780-d7dc014e7a61\matching_face_1788091869781.jpg"
    different_face_src = r"C:\Users\Arvindbhai\.gemini\antigravity-ide\brain\c83dd204-0809-4fd9-8780-d7dc014e7a61\different_face_1788091889808.jpg"
    
    if not os.path.exists(matching_face_src) or not os.path.exists(different_face_src):
        print("ERROR: Source face images not found!")
        return

    create_dirs()
    
    # CASE 1: Valid
    print("Generating Valid Case...")
    generate_passport(matching_face_src, "demo_data/valid/document.jpg")
    copy_file(matching_face_src, "demo_data/valid/matching_face.jpg")
    
    # CASE 2: Mismatch
    print("Generating Mismatch Case...")
    generate_passport(matching_face_src, "demo_data/mismatch/document.jpg")
    copy_file(different_face_src, "demo_data/mismatch/different_face.jpg")
    
    # CASE 3: Tampered
    print("Generating Tampered Case...")
    generate_passport(matching_face_src, "demo_data/tampered/document.jpg", tampered=True)
    copy_file(matching_face_src, "demo_data/tampered/matching_face.jpg")
    
    # CASE 4: Invalid Document
    print("Generating Invalid Document Case...")
    create_invalid_image("demo_data/invalid/invalid_document.jpg", "NOT A PASSPORT")
    copy_file(matching_face_src, "demo_data/invalid/invalid_face.jpg")
    
    # CASE 5: Invalid Face
    print("Generating Invalid Face Case...")
    generate_passport(matching_face_src, "demo_data/invalid/valid_document_invalid_face.jpg")
    create_invalid_image("demo_data/invalid/invalid_face_only.jpg", "NOT A FACE")

    print("Done!")

if __name__ == '__main__':
    main()

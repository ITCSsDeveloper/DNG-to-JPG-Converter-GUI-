import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import os
import rawpy
from PIL import Image, ExifTags
import threading
import math
import piexif
import exifread

# กำหนดค่า MPX ที่เลือกได้
MPX_OPTIONS = {
    "Original": None, # ใช้ None เพื่อระบุว่าให้คงขนาดเดิม
    "2 MPX": 2_000_000,
    "4 MPX": 4_000_000,
    "6 MPX": 6_000_000,
    "8 MPX": 8_000_000,
    "10 MPX": 10_000_000,
    "12 MPX": 12_000_000,
    "14 MPX": 14_000_000,
    "16 MPX": 16_000_000
}

# Dictionary to map exifread tag names to piexif tag IDs and their IFD
# This is a partial mapping, you might need to extend it for all possible tags
# that exifread can find and you want to preserve.
# For complex tags like GPS, we will handle them specifically.
EXIFREAD_TO_PIEXIF_MAP = {
    # 0th IFD (Image IFD)
    'Image Make': (piexif.ImageIFD.Make, 'bytes'),
    'Image Model': (piexif.ImageIFD.Model, 'bytes'),
    'Image Orientation': (piexif.ImageIFD.Orientation, 'int'),
    'Image Artist': (piexif.ImageIFD.Artist, 'bytes'),
    'Image Copyright': (piexif.ImageIFD.Copyright, 'bytes'),
    'Image Software': (piexif.ImageIFD.Software, 'bytes'),
    'Image DateTime': (piexif.ImageIFD.DateTime, 'bytes'), # Date and time of image creation

    # Exif IFD
    'EXIF ExposureTime': (piexif.ExifIFD.ExposureTime, 'rational'),
    'EXIF FNumber': (piexif.ExifIFD.FNumber, 'rational'),
    'EXIF ExposureProgram': (piexif.ExifIFD.ExposureProgram, 'int'),
    'EXIF ISOSpeedRatings': (piexif.ExifIFD.ISOSpeedRatings, 'int'),
    'EXIF SensitivityType': (piexif.ExifIFD.SensitivityType, 'int'), # Added from your image
    'EXIF RecommendedExposureIndex': (piexif.ExifIFD.RecommendedExposureIndex, 'long'), # Added
    'EXIF ExifVersion': (piexif.ExifIFD.ExifVersion, 'bytes'), # Added
    'EXIF DateTimeOriginal': (piexif.ExifIFD.DateTimeOriginal, 'bytes'),
    'EXIF DateTimeDigitized': (piexif.ExifIFD.DateTimeDigitized, 'bytes'),
    'EXIF ShutterSpeedValue': (piexif.ExifIFD.ShutterSpeedValue, 's_rational'), # Signed Rational
    'EXIF ApertureValue': (piexif.ExifIFD.ApertureValue, 'rational'),
    'EXIF ExposureBiasValue': (piexif.ExifIFD.ExposureBiasValue, 's_rational'), # Signed Rational
    'EXIF MaxApertureValue': (piexif.ExifIFD.MaxApertureValue, 'rational'),
    'EXIF MeteringMode': (piexif.ExifIFD.MeteringMode, 'int'),
    'EXIF Flash': (piexif.ExifIFD.Flash, 'int'),
    'EXIF FocalLength': (piexif.ExifIFD.FocalLength, 'rational'),
    'EXIF SubSecTimeOriginal': (piexif.ExifIFD.SubSecTimeOriginal, 'bytes'), # Added
    'EXIF SubSecTimeDigitized': (piexif.ExifIFD.SubSecTimeDigitized, 'bytes'), # Added
    'EXIF ColorSpace': (piexif.ExifIFD.ColorSpace, 'int'), # Added
    'EXIF FocalPlaneXResolution': (piexif.ExifIFD.FocalPlaneXResolution, 'rational'), # Added
    'EXIF FocalPlaneYResolution': (piexif.ExifIFD.FocalPlaneYResolution, 'rational'), # Added
    'EXIF FocalPlaneResolutionUnit': (piexif.ExifIFD.FocalPlaneResolutionUnit, 'int'), # Added
    'EXIF CustomRendered': (piexif.ExifIFD.CustomRendered, 'int'), # Added
    'EXIF ExposureMode': (piexif.ExifIFD.ExposureMode, 'int'), # Added
    'EXIF WhiteBalance': (piexif.ExifIFD.WhiteBalance, 'int'), # Added (note: also in 0th sometimes)
    'EXIF SceneCaptureType': (piexif.ExifIFD.SceneCaptureType, 'int'), # Added
    'EXIF BodySerialNumber': (piexif.ExifIFD.BodySerialNumber, 'bytes'), # Added
    'EXIF LensSpecification': (piexif.ExifIFD.LensSpecification, 'rational_list'), # Added, this is a list of rationals
    'EXIF LensModel': (piexif.ExifIFD.LensModel, 'bytes'), # Added
    'EXIF LensSerialNumber': (piexif.ExifIFD.LensSerialNumber, 'bytes'), # Added
    'EXIF ComponentsConfiguration': (piexif.ExifIFD.ComponentsConfiguration, 'bytes'),
    'EXIF FlashpixVersion': (piexif.ExifIFD.FlashpixVersion, 'bytes'),
    'EXIF PixelXDimension': (piexif.ExifIFD.PixelXDimension, 'int'),
    'EXIF PixelYDimension': (piexif.ExifIFD.PixelYDimension, 'int'),
    'EXIF SceneType': (piexif.ExifIFD.SceneType, 'bytes'), # Undefined type often maps to bytes
    'EXIF DigitalZoomRatio': (piexif.ExifIFD.DigitalZoomRatio, 'rational'),
    'EXIF FNumber': (piexif.ExifIFD.FNumber, 'rational'),
    # ... add more EXIF tags as needed from your exifread output
}

# Mapping for GPS tags (GPSIFD)
GPS_TAGS_MAP = {
    'GPS GPSVersionID': (piexif.GPSIFD.GPSVersionID, 'bytes_list'), # list of bytes (4 bytes)
    'GPS GPSLatitudeRef': (piexif.GPSIFD.GPSLatitudeRef, 'bytes'),
    'GPS GPSLatitude': (piexif.GPSIFD.GPSLatitude, 'rational_list'),
    'GPS GPSLongitudeRef': (piexif.GPSIFD.GPSLongitudeRef, 'bytes'),
    'GPS GPSLongitude': (piexif.GPSIFD.GPSLongitude, 'rational_list'),
    'GPS GPSAltitudeRef': (piexif.GPSIFD.GPSAltitudeRef, 'int'),
    'GPS GPSAltitude': (piexif.GPSIFD.GPSAltitude, 'rational'),
    'GPS GPSTimeStamp': (piexif.GPSIFD.GPSTimeStamp, 'rational_list'),
    'GPS GPSDate': (piexif.GPSIFD.GPSDateStamp, 'bytes'),
    'GPS GPSStatus': (piexif.GPSIFD.GPSStatus, 'bytes'),
    'GPS GPSMeasureMode': (piexif.GPSIFD.GPSMeasureMode, 'bytes'),
    'GPS GPSSpeedRef': (piexif.GPSIFD.GPSSpeedRef, 'bytes'),
    'GPS GPSSpeed': (piexif.GPSIFD.GPSSpeed, 'rational'),
    'GPS GPSTrackRef': (piexif.GPSIFD.GPSTrackRef, 'bytes'),
    'GPS GPSTrack': (piexif.GPSIFD.GPSTrack, 'rational'),
    'GPS GPSImgDirectionRef': (piexif.GPSIFD.GPSImgDirectionRef, 'bytes'),
    'GPS GPSImgDirection': (piexif.GPSIFD.GPSImgDirection, 'rational'),
    'GPS GPSMapDatum': (piexif.GPSIFD.GPSMapDatum, 'bytes'),
    'GPS GPSDestLatitudeRef': (piexif.GPSIFD.GPSDestLatitudeRef, 'bytes'),
    'GPS GPSDestLatitude': (piexif.GPSIFD.GPSDestLatitude, 'rational_list'),
    'GPS GPSDestLongitudeRef': (piexif.GPSIFD.GPSDestLongitudeRef, 'bytes'),
    'GPS GPSDestLongitude': (piexif.GPSIFD.GPSDestLongitude, 'rational_list'),
    'GPS GPSDestBearingRef': (piexif.GPSIFD.GPSDestBearingRef, 'bytes'),
    'GPS GPSDestBearing': (piexif.GPSIFD.GPSDestBearing, 'rational'),
    'GPS GPSDestDistanceRef': (piexif.GPSIFD.GPSDestDistanceRef, 'bytes'),
    'GPS GPSDestDistance': (piexif.GPSIFD.GPSDestDistance, 'rational'),
    # ... add more GPS tags
}


def get_piexif_ifd(exifread_tag_name):
    """Determines which piexif IFD a tag belongs to based on its name."""
    if exifread_tag_name.startswith('GPS'):
        return "GPS"
    elif exifread_tag_name.startswith('EXIF'):
        return "Exif"
    elif exifread_tag_name.startswith('Image'):
        return "0th"
    # You might need to add logic for "Interop" or "1st" IFD if necessary
    return None # Unknown IFD


def convert_exifread_value_to_piexif_format(exifread_tag_obj, data_type):
    """
    Converts exifread Tag object value to piexif compatible format.
    Handles common data types.
    """
    if exifread_tag_obj is None:
        return None

    if data_type == 'bytes':
        return str(exifread_tag_obj).encode('utf-8')
    elif data_type == 'int':
        return exifread_tag_obj.values[0]
    elif data_type == 'long': # For Long type which exifread also gives as int
        return exifread_tag_obj.values[0]
    elif data_type == 'rational':
        val = exifread_tag_obj.values[0]
        return (val.num, val.den)
    elif data_type == 's_rational': # Signed Rational
        val = exifread_tag_obj.values[0]
        # exifread.Rational handles negative num/den itself. piexif also needs (num, den)
        return (val.num, val.den)
    elif data_type == 'rational_list':
        # For tags like GPS Latitude/Longitude, which are list of rationals
        return [(val.num, val.den) for val in exifread_tag_obj.values]
    elif data_type == 'bytes_list': # For GPSVersionID which is a list of bytes/ints
        return tuple(exifread_tag_obj.values) # Convert list of ints to tuple of ints
    # Add more type handling if needed (e.g., undefined, ASCII lists, etc.)
    return None # Return None for unsupported types


def copy_exif_data(source_path, target_image):
    """
    คัดลอกข้อมูล EXIF ทั้งหมดจากไฟล์ต้นฉบับ (DNG หรือ JPG) ไปยังอ็อบเจกต์ Image ของ Pillow
    โดยใช้ exifread ในการอ่าน และ piexif ในการสร้างและบันทึก
    """
    exif_bytes_to_save = None
    piexif_exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}}

    try:
        # 1. อ่าน EXIF ด้วย exifread
        with open(source_path, 'rb') as f:
            tags = exifread.process_file(f, details=False) 
        
        print(f"Successfully loaded EXIF with exifread from {source_path}")
        
        # 2. วนลูปผ่านทุก Tag ที่ exifread ดึงมาได้
        for tag_name, tag_obj in tags.items():
            if tag_name in EXIFREAD_TO_PIEXIF_MAP:
                piexif_id, data_type = EXIFREAD_TO_PIEXIF_MAP[tag_name]
                ifd_name = get_piexif_ifd(tag_name)
                
                if ifd_name:
                    converted_value = convert_exifread_value_to_piexif_format(tag_obj, data_type)
                    if converted_value is not None:
                        piexif_exif_dict[ifd_name][piexif_id] = converted_value
                        # print(f"  Copied: {tag_name} ({ifd_name}) -> {converted_value}")
                else:
                    print(f"  Warning: Could not determine IFD for {tag_name}")
            elif tag_name in GPS_TAGS_MAP: # Handle GPS tags separately
                piexif_id, data_type = GPS_TAGS_MAP[tag_name]
                ifd_name = "GPS"
                converted_value = convert_exifread_value_to_piexif_format(tag_obj, data_type)
                if converted_value is not None:
                    piexif_exif_dict[ifd_name][piexif_id] = converted_value
                    # print(f"  Copied GPS: {tag_name} ({ifd_name}) -> {converted_value}")
            else:
                # print(f"  Skipping unsupported or unmapped EXIF tag: {tag_name}")
                pass # You can remove this or uncomment for debugging

        # 3. แปลง piexif_exif_dict กลับเป็น bytes เพื่อบันทึก
        if any(piexif_exif_dict[ifd] for ifd in piexif_exif_dict):
            # Clean up potentially empty IFDs before dumping, as piexif might complain
            # (though piexif.dump usually handles empty IFDs gracefully if they are empty dicts)
            
            exif_bytes_to_save = piexif.dump(piexif_exif_dict)
            print(f"EXIF data successfully dumped to bytes.")
        else:
            print("No relevant EXIF data found by exifread to copy or empty EXIF dict.")

    except exifread.exceptions.InvalidExifError:
        print(f"No valid EXIF data found in {source_path} using exifread.")
    except Exception as e_read:
        print(f"Error processing EXIF with exifread/piexif for {source_path}: {e_read}")

    # 4. กำหนด exif bytes ให้กับอ็อบเจกต์ Image ของ Pillow
    if exif_bytes_to_save:
        target_image.info['exif'] = exif_bytes_to_save
        print(f"EXIF bytes assigned to target image for saving.")
    else:
        if 'exif' in target_image.info:
            del target_image.info['exif']
        print(f"No EXIF data will be copied for {source_path}.")


def calculate_new_dimensions(original_width, original_height, target_mpx):
    """
    คำนวณขนาดใหม่ (width, height) เพื่อให้ได้จำนวนพิกเซลใกล้เคียง target_mpx
    โดยรักษาสัดส่วนภาพเดิม
    """
    if target_mpx is None: # Original size
        return original_width, original_height

    original_mpx = original_width * original_height
    
    if original_mpx <= target_mpx: # ถ้าภาพต้นฉบับเล็กกว่าหรือเท่ากับขนาดที่ต้องการ
        return original_width, original_height # ไม่ต้องขยายภาพ

    aspect_ratio = original_width / original_height
    
    # คำนวณความสูงใหม่จาก target_mpx และ aspect_ratio
    new_height = int(math.sqrt(target_mpx / aspect_ratio))
    new_width = int(new_height * aspect_ratio)

    return new_width, new_height

def convert_dng_to_jpg(input_folder, output_folder, target_mpx_value, jpg_quality, progress_var, status_label):
    """
    ฟังก์ชันหลักสำหรับแปลงไฟล์ DNG เป็น JPG พร้อมปรับขนาดและคุณภาพ
    """
    if not os.path.exists(input_folder):
        messagebox.showerror("Error", "Input folder does not exist.")
        return
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    dng_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.dng')]
    total_files = len(dng_files)
    if total_files == 0:
        status_label.config(text="No .dng files found in the input folder.")
        progress_var.set(100) # Complete the progress bar if no files
        return

    progress_var.set(0) # Reset progress
    
    for i, dng_file in enumerate(dng_files):
        dng_path = os.path.join(input_folder, dng_file)
        jpg_filename = os.path.splitext(dng_file)[0] + '.jpg'
        jpg_path = os.path.join(output_folder, jpg_filename)

        status_label.config(text=f"Converting: {dng_file} ({i+1}/{total_files})")
        
        try:
            with rawpy.imread(dng_path) as raw:
                rgb = raw.postprocess(
                    use_camera_wb=True,
                    output_color=rawpy.ColorSpace.sRGB,
                    no_auto_bright=True
                )
                
                image = Image.fromarray(rgb)
                
                # คัดลอก EXIF data ก่อนปรับขนาด
                # ตรงนี้จะเรียก copy_exif_data และมันจะจัดการใส่ EXIF bytes ลงใน image.info['exif'] ให้เอง
                copy_exif_data(dng_path, image)
              
                # ปรับขนาดภาพตาม MPX ที่เลือก
                if target_mpx_value is not None:
                    original_width, original_height = image.size
                    new_width, new_height = calculate_new_dimensions(original_width, original_height, target_mpx_value)
                    
                    if (new_width, new_height) != (original_width, original_height):
                        image = image.resize((new_width, new_height), Image.LANCZOS) # ใช้ LANCZOS เพื่อคุณภาพดีที่สุดในการลดขนาด

                # บันทึกเป็น JPG ด้วยคุณภาพที่กำหนด
                image.save(jpg_path, quality=jpg_quality, subsampling=0, exif=image.info.get('exif')) # subsampling=0 เพื่อคุณภาพสูงสุด

            # อัปเดต Progress Bar
            progress = (i + 1) / total_files * 100
            progress_var.set(progress)
            
        except Exception as e:
            messagebox.showerror("Conversion Error", f"Failed to convert {dng_file}: {e}")
            status_label.config(text=f"Error converting {dng_file}")
            break
    
    status_label.config(text="Conversion complete!")
    messagebox.showinfo("Done", "All DNG files converted to JPG!")


def start_conversion_thread(input_folder_path, output_folder_path, selected_mpx_option, selected_quality, progress_var, status_label):
    """
    เริ่มกระบวนการแปลงไฟล์ใน Thread แยกต่างหาก เพื่อไม่ให้ GUI ค้าง
    """
    if not input_folder_path.get() or not output_folder_path.get():
        messagebox.showwarning("Warning", "Please select both input and output folders.")
        return
        
    # ดึงค่า MPX จริงจากที่เลือก
    target_mpx = MPX_OPTIONS[selected_mpx_option.get()]
    jpg_quality = selected_quality.get() # ดึงค่าจาก tk.IntVar() ซึ่งเป็น Integer อยู่แล้ว

    start_button.config(state=tk.DISABLED)
    progress_bar.pack(pady=10)
    
    conversion_thread = threading.Thread(target=convert_dng_to_jpg, 
                                         args=(input_folder_path.get(), 
                                               output_folder_path.get(), 
                                               target_mpx, 
                                               jpg_quality,
                                               progress_var, 
                                               status_label))
    conversion_thread.start()
    
    root.after(100, check_thread_status, conversion_thread)

def check_thread_status(thread):
    if thread.is_alive():
        root.after(100, check_thread_status, thread)
    else:
        start_button.config(state=tk.NORMAL)
        progress_bar.pack_forget()

# --- ฟังก์ชันสำหรับอัปเดตค่า Quality Slider ให้เป็นจำนวนเต็ม ---
def update_quality_value(val):
    """เมื่อ Slider ถูกเลื่อน, ปัดเศษค่าให้เป็นจำนวนเต็มและอัปเดต tk.IntVar"""
    selected_quality.set(int(float(val)))


# --- GUI Setup ---
root = tk.Tk()
root.title("DNG to JPG Converter")
root.geometry("500x450") # เพิ่มขนาดหน้าต่าง
root.resizable(False, False)

# Variables
input_folder_path = tk.StringVar()
output_folder_path = tk.StringVar()
progress_var = tk.DoubleVar()
selected_mpx_option = tk.StringVar(value="Original") # ค่าเริ่มต้น

# ใช้ tk.IntVar() สำหรับ quality เพื่อให้เป็น Integer โดยตรง
selected_quality = tk.IntVar(value=90) # ค่าเริ่มต้น

# Input Folder Selection
input_frame = tk.LabelFrame(root, text="Input Folder (DNG files)")
input_frame.pack(padx=20, pady=10, fill="x")

input_entry = tk.Entry(input_frame, textvariable=input_folder_path, width=50)
input_entry.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")

input_button = tk.Button(input_frame, text="Browse", 
                         command=lambda: input_folder_path.set(filedialog.askdirectory()))
input_button.pack(side=tk.RIGHT, padx=5, pady=5)

# Output Folder Selection
output_frame = tk.LabelFrame(root, text="Output Folder (JPG files)")
output_frame.pack(padx=20, pady=10, fill="x")

output_entry = tk.Entry(output_frame, textvariable=output_folder_path, width=50)
output_entry.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")

output_button = tk.Button(output_frame, text="Browse", 
                          command=lambda: output_folder_path.set(filedialog.askdirectory()))
output_button.pack(side=tk.RIGHT, padx=5, pady=5)

# Image Options Frame
options_frame = tk.LabelFrame(root, text="Image Options")
options_frame.pack(padx=20, pady=10, fill="x")

# MPX Selection
mpx_label = tk.Label(options_frame, text="Output MPX:")
mpx_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
mpx_dropdown = ttk.Combobox(options_frame, textvariable=selected_mpx_option, 
                            values=list(MPX_OPTIONS.keys()), state="readonly", width=15)
mpx_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

# JPG Quality Slider
quality_label = tk.Label(options_frame, text="JPG Quality (1-100):")
quality_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")

# !!! การเปลี่ยนแปลงที่นี่ !!!
# เพิ่ม command=update_quality_value เพื่อให้เรียกฟังก์ชันนี้ทุกครั้งที่ Slider ถูกเลื่อน
quality_slider = ttk.Scale(options_frame, from_=1, to=100, orient="horizontal", 
                           variable=selected_quality, length=200, 
                           command=update_quality_value) # <--- เพิ่มบรรทัดนี้
quality_slider.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

# เพิ่ม Label แสดงค่า Quality ปัจจุบัน (จะแสดงเป็น Integer อัตโนมัติเพราะผูกกับ tk.IntVar)
quality_value_label = tk.Label(options_frame, textvariable=selected_quality)
quality_value_label.grid(row=1, column=2, padx=5, pady=5, sticky="w")

options_frame.grid_columnconfigure(1, weight=1) # ให้ Combobox และ Slider ขยายเต็มพื้นที่

# Start Conversion Button
start_button = tk.Button(root, text="Start Conversion", font=("Arial", 12, "bold"),
                         command=lambda: start_conversion_thread(input_folder_path, output_folder_path, 
                                                                 selected_mpx_option, selected_quality,
                                                                 progress_var, status_label))
start_button.pack(pady=15)

# Progress Bar
progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100, length=400, mode='determinate')

# Status Label
status_label = tk.Label(root, text="Ready to convert...", font=("Arial", 10))
status_label.pack(pady=5)

root.mainloop()
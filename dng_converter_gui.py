import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import os
import rawpy
from PIL import Image, ExifTags
import threading
import math

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

def copy_exif_data(source_path, target_image):
    """
    คัดลอกข้อมูล EXIF จากไฟล์ต้นฉบับไปยังอ็อบเจกต์ Image ของ Pillow
    """
    try:
        with Image.open(source_path) as img:
            if hasattr(img, '_getexif'):
                exif_data = img.info.get('exif') # ดึง EXIF bytes ดิบ (ถ้ามี)
                if exif_data:
                    target_image.info['exif'] = exif_data
                # ถ้าไม่มี exif_data bytes, เราจะข้ามไปก่อนเพื่อความเรียบง่าย
                # หากต้องการความสมบูรณ์ในการคัดลอก EXIF ทุกแท็ก อาจพิจารณาใช้ piexif
                # import piexif
                # exif_dict = img._getexif()
                # if exif_dict:
                #     exif_bytes = piexif.dump(exif_dict)
                #     target_image.info['exif'] = exif_bytes
                
    except Exception as e:
        print(f"Error copying EXIF from {source_path}: {e}")

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
                copy_exif_data(dng_path, image)

                # ปรับขนาดภาพตาม MPX ที่เลือก
                if target_mpx_value is not None:
                    original_width, original_height = image.size
                    new_width, new_height = calculate_new_dimensions(original_width, original_height, target_mpx_value)
                    
                    if (new_width, new_height) != (original_width, original_height):
                        image = image.resize((new_width, new_height), Image.LANCZOS) # ใช้ LANCZOS เพื่อคุณภาพดีที่สุดในการลดขนาด

                # บันทึกเป็น JPG ด้วยคุณภาพที่กำหนด
                image.save(jpg_path, quality=jpg_quality, subsampling=0) # subsampling=0 เพื่อคุณภาพสูงสุด

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
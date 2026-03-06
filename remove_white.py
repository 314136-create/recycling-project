from PIL import Image
import os

# Open the original cat image
img_path = r"C:\Users\huang\OneDrive\桌面\資處科專題\coffee\static\cat.png"
img = Image.open(img_path)

# Convert to RGBA if not already
img = img.convert("RGBA")

# Get pixel data
datas = img.getdata()

# Replace white pixels with transparent
newData = []
for item in datas:
    # If pixel is white or near-white (R, G, B all > 250)
    if item[0] > 250 and item[1] > 250 and item[2] > 250:
        # Make it transparent
        newData.append((255, 255, 255, 0))
    else:
        newData.append(item)

img.putdata(newData)

# Save with transparency
output_path = r"C:\Users\huang\OneDrive\桌面\資處科專題\coffee\static\cat.png"
img.save(output_path, "PNG")
print("Done! White background removed.")

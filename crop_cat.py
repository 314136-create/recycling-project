from PIL import Image

# Open the cat image
img = Image.open('static/cat.png')
print('Original size:', img.size)

# Crop only the top portion (cat head and tail, remove the cup)
# Keep top 50% of the image
cropped = img.crop((0, 0, img.width, int(img.height * 0.50)))
print('Cropped size:', cropped.size)

# Save the cropped image
cropped.save('static/cat_only.png')
print('Saved to static/cat_only.png')

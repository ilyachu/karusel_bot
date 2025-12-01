import logging
from services.image_renderer import render_slide
import os

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_rendering():
    print("Testing render_slide...")
    
    # Use a dummy image URL or local path (create a dummy file)
    dummy_bg = "dummy_bg.png"
    from PIL import Image
    Image.new("RGB", (1080, 1350), "blue").save(dummy_bg)
    
    try:
        # Test Top
        print("Rendering Top...")
        img_io = render_slide(dummy_bg, "Title Top", "Body text here", "top")
        with open("test_slide_top.png", "wb") as f:
            f.write(img_io.getbuffer())
            
        # Test Center
        print("Rendering Center...")
        img_io = render_slide(dummy_bg, "Title Center", "Body text here", "center")
        with open("test_slide_center.png", "wb") as f:
            f.write(img_io.getbuffer())
            
        # Test Bottom
        print("Rendering Bottom...")
        img_io = render_slide(dummy_bg, "Title Bottom", "Body text here", "bottom")
        with open("test_slide_bottom.png", "wb") as f:
            f.write(img_io.getbuffer())
            
        print("Done. Check test_slide_*.png files.")
        
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        if os.path.exists(dummy_bg):
            os.remove(dummy_bg)

if __name__ == "__main__":
    test_rendering()

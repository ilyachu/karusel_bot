from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
from io import BytesIO
import os
import logging

# Constants
WIDTH = 1080
HEIGHT = 1350
PADDING_X = 80
PADDING_Y = 100
LOGO_TEXT = "chu ai"

def render_slide(bg_source, title: str, body: str, text_position: str = "center", font_style: str = "standard", logo_text: str = None) -> BytesIO:
    """
    Render a slide with text overlay on a background.
    
    Args:
        bg_source: Either a URL string or BytesIO object containing the background image
        title: Title text for the slide
        body: Body text for the slide
        text_position: Position of text ("top", "center", or "bottom")
        font_style: Font style ("standard", "elegant", "rough")
        logo_text: Custom logo text (optional, defaults to global constant)
    
    Returns:
        BytesIO object containing the rendered PNG image
    """
    output = BytesIO()
    try:
        # 1. Load Background
        if isinstance(bg_source, BytesIO):
            # BytesIO object - custom uploaded background
            bg_source.seek(0)
            bg_img = Image.open(bg_source).convert("RGBA")
        elif isinstance(bg_source, str) and bg_source.startswith("http"):
            # URL string - download from web
            response = requests.get(bg_source)
            response.raise_for_status()
            bg_img = Image.open(BytesIO(response.content)).convert("RGBA")
        elif isinstance(bg_source, str):
            # Local file path
            if os.path.exists(bg_source):
                bg_img = Image.open(bg_source).convert("RGBA")
            else:
                bg_img = Image.new("RGBA", (WIDTH, HEIGHT), (50, 50, 50, 255))
        else:
            # Fallback for unknown types
            bg_img = Image.new("RGBA", (WIDTH, HEIGHT), (50, 50, 50, 255))

        # Resize/Crop to cover
        bg_img = ImageOps.fit(bg_img, (WIDTH, HEIGHT))
        
        # 2. Add Overlay (Darken)
        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 120)) # Semi-transparent black
        img = Image.alpha_composite(bg_img, overlay)
        img = img.convert("RGB") # Convert back to RGB for saving
        
        draw = ImageDraw.Draw(img)
        
        # 3. Load Fonts
        font_paths = {
            "standard": "assets/fonts/font.ttf",
            "elegant": "assets/fonts/elegant.ttf",
            "rough": "assets/fonts/rough.ttf",
            "prosto": "assets/fonts/ProstoOne-Regular.ttf",
            "rampart": "assets/fonts/RampartOne-Regular.ttf",
            "dela": "assets/fonts/DelaGothicOne-Regular.ttf"
        }
        
        selected_font_path = font_paths.get(font_style, "assets/fonts/font.ttf")
        
        try:
            # Try to load custom font if exists
            logging.info(f"Attempting to load font from: {selected_font_path}")
            if os.path.exists(selected_font_path):
                title_font = ImageFont.truetype(selected_font_path, 90)
                body_font = ImageFont.truetype(selected_font_path, 52)
                logo_font = ImageFont.truetype(selected_font_path, 40)
                logging.info(f"Custom font '{font_style}' loaded successfully.")
            else:
                # Try fallback to standard if specific style missing
                fallback_path = "assets/fonts/font.ttf"
                if os.path.exists(fallback_path):
                    logging.warning(f"Font {selected_font_path} not found, using standard.")
                    title_font = ImageFont.truetype(fallback_path, 90)
                    body_font = ImageFont.truetype(fallback_path, 52)
                    logo_font = ImageFont.truetype(fallback_path, 40)
                else:
                    raise FileNotFoundError("No custom fonts found")
        except Exception as e:
            logging.error(f"Failed to load custom font: {e}")
            # Fallback to default
            title_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
            logo_font = ImageFont.load_default()
            
        # 4. Text Wrapping Helper
        def wrap_text(text, font, max_width):
            lines = []
            words = text.split()
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=font)
                w = bbox[2] - bbox[0]
                if w <= max_width:
                    current_line.append(word)
                else:
                    lines.append(' '.join(current_line))
                    current_line = [word]
            lines.append(' '.join(current_line))
            return lines

        # 5. Calculate Text Height
        max_text_width = WIDTH - 2 * PADDING_X
        
        title_lines = wrap_text(title, title_font, max_text_width)
        body_lines = wrap_text(body, body_font, max_text_width)
        
        # Calculate total height of text block
        # Approximate height using bbox
        title_h = sum([draw.textbbox((0, 0), line, font=title_font)[3] - draw.textbbox((0, 0), line, font=title_font)[1] + 10 for line in title_lines])
        body_h = sum([draw.textbbox((0, 0), line, font=body_font)[3] - draw.textbbox((0, 0), line, font=body_font)[1] + 10 for line in body_lines])
        gap = 40
        total_text_height = title_h + gap + body_h
        
        # 6. Determine Y Position
        # 6. Determine Y Position
        logging.info(f"Text Position requested: {text_position}")
        logging.info(f"Total text height: {total_text_height}")
        
        if text_position == "top":
            start_y = PADDING_Y + 100
        elif text_position == "bottom":
            start_y = HEIGHT - PADDING_Y - total_text_height - 100
        else: # center
            start_y = (HEIGHT - total_text_height) // 2
            
        logging.info(f"Calculated start_y: {start_y}")
            
        # 7. Draw Text
        current_y = start_y
        
        # Title - Left aligned with larger font
        for line in title_lines:
            # Left align text with padding
            x = PADDING_X
            draw.text((x, current_y), line, font=title_font, fill="white")
            bbox = draw.textbbox((0, 0), line, font=title_font)
            current_y += (bbox[3] - bbox[1]) + 15  # Increased spacing
            
        current_y += gap
        
        # Body - Left aligned
        for line in body_lines:
            x = PADDING_X
            draw.text((x, current_y), line, font=body_font, fill="#eeeeee")  # Brighter text
            bbox = draw.textbbox((0, 0), line, font=body_font)
            current_y += (bbox[3] - bbox[1]) + 12  # Better line spacing
            
        # 8. Draw Logo (Bottom Center)
        final_logo = logo_text if logo_text else LOGO_TEXT
        bbox = draw.textbbox((0, 0), final_logo, font=logo_font)
        w = bbox[2] - bbox[0]
        x = (WIDTH - w) // 2
        y = HEIGHT - PADDING_Y
        draw.text((x, y), final_logo, font=logo_font, fill="#999999")  # Lighter logo
        
        # 9. Save to Buffer
        img.save(output, format="PNG")
        output.seek(0)
        return output
        
    except Exception as e:
        logging.error(f"Error in render_slide: {e}")
        # Return a blank image with error text if possible, or just gray
        img = Image.new("RGB", (1080, 1350), color="gray")
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.load_default()
            draw.text((50, 50), "Error rendering slide", fill="red", font=font)
        except:
            pass
        img.save(output, format="PNG")
        output.seek(0)
        return output

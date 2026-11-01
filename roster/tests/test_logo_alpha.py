import unittest
try:
    from PIL import Image
except ImportError:
    Image = None
from roster.logos import transparent_background


@unittest.skipIf(Image is None, 'Pillow is only required for local game conversion')
class LogoAlphaTests(unittest.TestCase):
    def test_exterior_white_removed_internal_white_preserved(self):
        image = Image.new('RGBA',(7,7),'white')
        for x in range(1,6):
            for y in range(1,6):
                image.putpixel((x,y),(0,90,20,255))
        image.putpixel((3,3),(255,255,255,255))
        result = transparent_background(image)
        self.assertEqual(result.getpixel((0,0))[3],0)
        self.assertEqual(result.getpixel((3,3)),(255,255,255,255))
        self.assertEqual(result.getpixel((1,1)),image.getpixel((1,1)))
        self.assertEqual(image.getpixel((0,0))[3],255)

    def test_colored_background_and_original_transparency_preserved(self):
        image = Image.new('RGBA',(5,5),(220,170,10,255))
        self.assertEqual(transparent_background(image).tobytes(),image.tobytes())
        clear = Image.new('RGBA',(5,5),(0,0,0,0))
        clear.putpixel((2,2),(10,20,30,255))
        self.assertEqual(transparent_background(clear).tobytes(),clear.tobytes())

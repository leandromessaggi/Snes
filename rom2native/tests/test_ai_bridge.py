import unittest
from rom2native.ai_bridge import png_dimensions,prepare_workflow,check_server
from rom2native.romtool import png_rgb

class AIBridgeTests(unittest.TestCase):
    def test_png_dimensions(self):
        img=png_rgb(8,8,bytes(8*8*3))
        self.assertEqual(png_dimensions(img),(8,8))
        with self.assertRaises(ValueError): png_dimensions(b"notpng")
    def test_workflow_injection(self):
        original={"10":{"class_type":"LoadImage","inputs":{"image":"old.png"}},
                  "20":{"class_type":"CLIPTextEncode","inputs":{"text":"old"}}}
        updated=prepare_workflow(original,"10","20","sprite.png","PS1 CGI")
        self.assertEqual(updated["10"]["inputs"]["image"],"sprite.png")
        self.assertEqual(updated["20"]["inputs"]["text"],"PS1 CGI")
        self.assertEqual(original["10"]["inputs"]["image"],"old.png")
        with self.assertRaises(ValueError):
            prepare_workflow(original,"11","20","x","y")
    def test_remote_requires_consent(self):
        self.assertEqual(check_server("http://127.0.0.1:8188/",False),"http://127.0.0.1:8188")
        with self.assertRaises(ValueError):
            check_server("https://example.com",False)
        self.assertEqual(check_server("https://example.com",True),"https://example.com")

if __name__=="__main__":unittest.main()

"""SVG clipping must preserve the mathematics shown in the browser."""
import base64
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import practice_tutor as T
from knowledge_graph import question_fingerprint
from student_assessment import AssessmentError

ROOT=Path(__file__).resolve().parents[1]


class SvgRenderingTests(unittest.TestCase):
    def test_even_odd_clip_detection_does_not_confuse_ordinary_fill(self):
        self.assertTrue(T._evenodd_clipping(b'<svg><clipPath><path clip-rule="evenodd"/></clipPath></svg>'))
        self.assertTrue(T._evenodd_clipping(b'<svg><clipPath><path style="clip-rule: evenodd"/></clipPath></svg>'))
        self.assertFalse(T._evenodd_clipping(b'<svg><path fill-rule="evenodd"/></svg>'))

    def test_missing_browser_explicitly_fails_instead_of_using_wrong_mupdf(self):
        with patch.object(T,'_svg_browser',return_value=None):
            with self.assertRaises(AssessmentError)as caught:T._browser_svg_png(Path('unused.svg'),100,100)
        self.assertEqual(caught.exception.status,503)
        self.assertIn('shared system or user installation',str(caught.exception))

    def test_timeout_is_reported_without_silent_renderer_fallback(self):
        with tempfile.TemporaryDirectory()as folder:
            path=Path(folder)/'figure.svg';path.write_text('<svg/>')
            with patch.object(T,'_svg_browser',return_value='shared-browser'),patch.object(T.subprocess,'run',side_effect=subprocess.TimeoutExpired('browser',20)):
                with self.assertRaises(AssessmentError)as caught:T._browser_svg_png(path,100,100)
        self.assertEqual(caught.exception.status,502)

    def test_browser_uses_argv_offline_image_and_private_temporary_profile(self):
        observed={}
        with tempfile.TemporaryDirectory()as folder:
            path=Path(folder)/'figure & source.svg';original=b'<svg/>';path.write_bytes(original)
            def run(argv,**kwargs):
                observed.update(argv=argv,kwargs=kwargs)
                screenshot=Path(next(s.split('=',1)[1]for s in argv if s.startswith('--screenshot=')))
                observed['temporary']=screenshot.parent
                html=(screenshot.parent/'image.html').read_text()
                self.assertIn("default-src 'none'",html);self.assertIn('img-src file: data:',html)
                self.assertIn(path.resolve().as_uri(),html);self.assertNotIn('<script',html)
                Image.new('RGB',(512,512),'white').save(screenshot)
                return subprocess.CompletedProcess(argv,0)
            with patch.object(T,'_svg_browser',return_value='shared-browser'),patch.object(T.subprocess,'run',side_effect=run):
                image=Image.open(io.BytesIO(T._browser_svg_png(path,100,120)))
            self.assertEqual(image.size,(100,120));self.assertEqual(path.read_bytes(),original)
        self.assertIsInstance(observed['argv'],list);self.assertNotIn('shell',observed['kwargs'])
        self.assertEqual(observed['kwargs']['timeout'],20);self.assertFalse(observed['temporary'].exists())
        if os.name=='nt':self.assertEqual(observed['kwargs']['creationflags'],subprocess.CREATE_NO_WINDOW)

    def test_browser_failure_does_not_return_an_incorrect_image(self):
        with tempfile.TemporaryDirectory()as folder:
            path=Path(folder)/'figure.svg';path.write_text('<svg/>')
            with patch.object(T,'_svg_browser',return_value='shared-browser'),patch.object(T.subprocess,'run',return_value=subprocess.CompletedProcess([],1)):
                with self.assertRaises(AssessmentError):T._browser_svg_png(path,100,100)

    def test_ordinary_svg_keeps_existing_native_renderer_and_margin(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);figures=root/'amc-bank/figures';figures.mkdir(parents=True)
            (figures/'simple.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="red"/></svg>')
            question={'ID':'2020_AMC_8_Q01','Bank':'amc','Question':'[Figure 1](figures/simple.svg)','Choices':{},'Solution':'','Meta':{}}
            with patch.object(T,'_browser_svg_png',side_effect=AssertionError('Ordinary SVG must not launch a browser')):
                urls,names=T.question_images(question,root)
            image=Image.open(io.BytesIO(base64.b64decode(urls[0].split(',')[1])))
            self.assertEqual(names,['figures/simple.svg']);self.assertEqual(image.getpixel((0,0)),(255,255,255));self.assertEqual(image.getpixel((100,100)),(255,0,0))


@unittest.skipUnless(T._svg_browser(),'Actual even-odd SVG regressions need a shared Chrome, Chromium or Edge installation.')
class ActualEvenOddFigures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.images={}
        for qid in('2011_AMC_12A_Q02','2011_AMC_12A_Q11','2014_AMC_10A_Q12','2023_AMC_8_Q12'):
            path=ROOT/'amc-bank/questions'/(qid+'.json');question=json.loads(path.read_text(encoding='utf-8'))
            before=question_fingerprint(question,ROOT);source=ROOT/'amc-bank'/next(iter(before['figureHashes']));source_bytes=source.read_bytes()
            urls,names=T.question_images(question,ROOT)
            if len(urls)!=1:raise AssertionError('Expected the exact one displayed source figure.')
            cls.images[qid]=Image.open(io.BytesIO(base64.b64decode(urls[0].split(',')[1]))).convert('RGB')
            if source.read_bytes()!=source_bytes or question_fingerprint(question,ROOT)!=before:raise AssertionError('Rendering changed the original source binding.')

    def test_coin_occlusion_hides_lower_arc_but_preserves_upper_coin_boundary(self):
        image=self.images['2011_AMC_12A_Q02']
        # A's lower-right boundary lies beneath C; C's top boundary stays visible.
        self.assertEqual(image.getpixel((468+12,304+12)),(255,255,255))
        self.assertLess(max(image.getpixel((631+12,149+12))),40)

    def test_circle_overlap_lenses_remain_unshaded(self):
        image=self.images['2011_AMC_12A_Q11']
        self.assertEqual(image.getpixel((344+12,344+12)),(255,255,255))
        r,g,b=image.getpixel((442+12,98+12));self.assertGreater(b,max(r,g)+30)

    def test_hexagon_vertex_sectors_are_white_and_center_is_shaded(self):
        image=self.images['2014_AMC_10A_Q12']
        self.assertEqual(image.getpixel((227+12,93+12)),(255,255,255))
        r,g,b=image.getpixel((450+12,390+12));self.assertGreater(b,max(r,g)+80)

    def test_circle_probability_figure_preserves_both_holes(self):
        image=self.images['2023_AMC_8_Q12']
        for x,y in((140,430),(440,430)):self.assertEqual(image.getpixel((x+12,y+12)),(255,255,255))
        for x,y in((290,210),(675,225)):
            r,g,b=image.getpixel((x+12,y+12));self.assertGreater(b,max(r,g)+80)


if __name__=='__main__':unittest.main(verbosity=2)

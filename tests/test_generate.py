import datetime as dt
import sys
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import generate

class GeneratorTests(unittest.TestCase):
    def test_offline_svg_is_valid_xml_and_escaped(self):
        card=generate.render_card({'repos':1,'stars':2,'commits':3,'contribs':4},'@< &\n# "', 'dark','2026-11-17')
        ET.fromstring(card)
        self.assertIn('@&lt; &amp;',card)
        self.assertIn('Commits',card)

    def test_heatmap_levels(self):
        self.assertEqual([generate.heat_level(n) for n in (0,1,3,6,10)],[0,1,2,3,4])

    def test_heatmap_renders_contribution_day(self):
        d=dt.date(2026,11,17)
        heat=generate.render_heatmap({'contribs':8,'calendar':[{'contributionDays':[{'date':d.isoformat(),'contributionCount':8}]}]},'light','2026-11-17')
        ET.fromstring(heat)
        self.assertIn('8 contributions',heat)

    def test_missing_stats_are_not_invented(self):
        card=generate.render_card({},'@\n@\n','light','preview')
        ET.fromstring(card)
        self.assertIn('—',card)
        self.assertIn('preview',card)

if __name__=='__main__':unittest.main()

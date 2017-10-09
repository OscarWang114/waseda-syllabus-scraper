# -*- coding: utf-8 -*-
from scrapy.linkextractors import LinkExtractor
from scrapy.loader import ItemLoader
from scrapy.spiders import Rule
from scrapy.http import FormRequest
from scrapy.spiders import Spider
from scrapy.utils.response import open_in_browser
from scrapy.utils.python import to_bytes
from selenium import webdriver

from wsl_spider.items import FirstResultPage
import os
import tempfile


class SearchSpider(Spider):
    name = 'search'
    allowed_domains = ['wsl.waseda.jp']
    start_urls = ['https://www.wsl.waseda.jp/syllabus/JAA101.php?pLng=en']
    target = 'Sports Sci'
    school_dict = {
        'Sports Sci': "202003",
        'Political Sci': "111973",
        'Fund Sci/Eng': "262006",
        'Cre Sci/Eng': "272006",
        'Adv Sci/Eng': "282006"
    }
    form_data = {
        'keyword': "",
        "s_bunya1_hid": "Please select the First Academic disciplines.",
        "s_bunya2_hid": "Please select the Second Academic disciplines.",
        "s_bunya3_hid": "Please select the Third Academic disciplines.",
        "area_type": "",
        "area_value": "",
        "s_level_hid": "",
        "kamoku": "",
        "kyoin": "",
        "p_gakki": "2",
        "p_youbi": "",
        "p_jigen": "",
        "p_gengo": "",
        "p_gakubu": school_dict[target],
        "p_keya": "",
        "p_searcha": "a",
        "p_keyb": "",
        "p_searchb": "b",
        "hidreset": "",
        "pfrontPage": "now",
        "pchgFlg": "",
        "bunya1_hid": "",
        "bunya2_hid": "",
        "bunya3_hid": "",
        "level_hid": "",
        "ControllerParameters": "JAA103SubCon",
        "pOcw": "",
        "pType": "",
        "pLng": "en"
    }

    rules = (
        Rule(
            LinkExtractor(restrict_xpaths=('(//table[@class="t-btn"])[2]/tbody/tr/td/div/div/p/a')),
            callback='parse_result_page'
        ),
    )

    def __init__(self):
        self.driver = webdriver.Chrome('/Users/oscar/chromedriver')
        return

    def parse(self, response):
        return FormRequest.from_response(
            response,
            formdata=self.form_data,
            callback=self.after_search
        )

    def after_search(self, response):
        # first_page_loader = ItemLoader(item=FirstResultPage(), response=response)
        # first_page_loader.add_value('name', self.target)
        # first_page_loader.add_value('html', response.body)
        # return first_page_loader.load_item()

        return self.open_in_driver(response)

    def open_in_driver(self, response):

        from scrapy.http import HtmlResponse
        # XXX: this implementation is a bit dirty and could be improved
        body = response.body
        if isinstance(response, HtmlResponse):
            if b'<base' not in body:
                repl = '<head><base href="%s">' % response.url
                body = body.replace(b'<head>', to_bytes(repl))
            ext = '.html'
        else:
            raise TypeError("Unsupported response type: %s" %
                            response.__class__.__name__)
        fd, fname = tempfile.mkstemp(ext)
        os.write(fd, body)
        os.close(fd)
        return self.driver.get("file://%s" % fname)

    def parse_result_page(self, response):
        # self.logger.info('Hi, this is a result page! %s', response.url)
        return

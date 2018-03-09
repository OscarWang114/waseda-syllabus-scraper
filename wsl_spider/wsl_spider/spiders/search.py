# -*- coding: utf-8 -*-
import re
import logging

from scrapy.exceptions import CloseSpider
from scrapy.http import Request
from scrapy.selector import Selector
from scrapy.spiders import Spider

from wsl_spider.items import CourseLoader, OccurrenceLoader


############################
# TODO https://www.wsl.waseda.jp/syllabus/js/custom/JAA103/JAA103.js
# TODO You can find the key in <a onclick></a> and insert it into JAA104.php to ge full detail of syllabus
############################

# These two schools return little course results and are good for testing.
art_architecture = "art_architecture"
sports_sci = "sports_sci"

sils = "sils"
poli_sci = "poli_sci"
fund_sci_eng = "fund_sci_eng"
cre_sci_eng = "cre_sci_eng"
adv_sci_eng = "adv_sci_eng"

# Returns results of every school.
all_school = "all"


def customize_url(url, lang, term, school, results_per_page, start_page):
    langs = {'eng': "en", 'jp': "jp"}
    terms = {'full_year': "0", 'spring_summer': "1", 'fall_winter': "2", 'others': "9"}
    schools = {
        'art_architecture': "712001",
        'sports_sci': "202003",
        'sils': "212004",
        'poli_sci': "111973",
        'fund_sci_eng': "262006",
        'cre_sci_eng': "272006",
        'adv_sci_eng': "282006",
        'all': ""
    }
    # Use dict to represent enum
    results_per_page_dict = {'10': "10", '20': "20", '50': "50", '100': "100"}

    lang_param = 'pLng=' + langs[lang]
    term_param = 'p_gakki=' + terms[term]
    school_param = 'p_gakubu=' + schools[school]
    results_per_page_param = 'p_number=' + results_per_page_dict[str(results_per_page)]
    start_page_param = 'p_page=' + str(start_page)
    params = ([lang_param, term_param, school_param, results_per_page_param, start_page_param])
    return url + '&'.join(params)


class SearchSpider(Spider):
    name = 'search'
    allowed_domains = ['wsl.waseda.jp']
    basic_url = 'https://www.wsl.waseda.jp/syllabus/JAA103.php?'
    close_spider_msg = "There are no more urls to scrape. Closing spider."
    reach_lower_bound_year_msg = "Scraped data has reached lower bound year {}"

    # Change the target semester, school, and other parameters here.
    lang = 'eng'
    year = 2018
    term = 'spring_summer'
    schools = [fund_sci_eng, cre_sci_eng, adv_sci_eng]
    start_school = schools[0]
    results_per_page = 100
    start_page = 1
    start_url = customize_url(basic_url, lang, term, start_school, results_per_page, start_page)
    start_urls = [start_url]

    year_str = str(year)
    year_lower_bound = str(year - 1)
    current_school = start_school
    current_page = start_page
    current_url = start_url

    def parse(self, response):
        reached_lower_bound_year = False
        sel = Selector(response=response, type="html")
        c_infos = sel.xpath('//table[@class="ct-vh"]/tbody/tr[not(@class="c-vh-title")]')
        for c_info in c_infos:
            year = c_info.xpath('td[1]/text()').extract_first()
            if year <= self.year_lower_bound:
                reached_lower_bound_year = True
            cl = CourseLoader(selector=c_info)

            cl.add_value(field_name='year', value=year)
            cl.add_xpath(field_name='code', xpath='td[2]/text()')
            cl.add_xpath(field_name='title', xpath='td[3]/a/text()')
            cl.add_xpath(field_name='instructor', xpath='td[4]/text()')
            cl.add_xpath(field_name='school', xpath='td[5]/text()')
            cl.add_xpath(field_name='term', xpath='td[6]/text()')

            link = c_info.xpath('td[3]/a/@onclick').extract()
            cl.add_value(field_name='link', value=link)

            day_periods = c_info.xpath('td[7]/text()').extract()
            locations = c_info.xpath('td[8]/text()').extract()

            for day_period, location in zip(day_periods, locations):
                ol = OccurrenceLoader()
                day_period_match = re.match(
                    r'(\d{2}:)?(?P<day>[A-Z][a-z]*).(?P<start>\d)?-?(?P<end>\d)', day_period
                )

                if day_period_match is None:
                    day_period_match = re.match(
                        r'(\d{2}:)?(?P<value>.*)', day_period
                    )
                    value = day_period_match.group('value')
                    day = value
                    start_period = value
                    end_period = value
                    start_time = self.period_to_minutes(value)
                    end_time = self.period_to_minutes(value)
                else:
                    day = day_period_match.group('day')
                    start_period = day_period_match.group('start')
                    end_period = day_period_match.group('end')
                    if start_period is None:
                        start_period = end_period
                    start_time = self.period_to_minutes(start_period + 's')
                    end_time = self.period_to_minutes(end_period + 'e')

                ol.add_value(field_name='day', value=day)
                ol.add_value(field_name='start_period', value=start_period)
                ol.add_value(field_name='end_period', value=end_period)
                ol.add_value(field_name='start_time', value=int(start_time))
                ol.add_value(field_name='end_time', value=int(end_time))

                location_match = re.match(
                    r'(\d{2}:)?(?P<building>\d+)-(?P<classroom>.*)', location
                )

                if location_match is None:
                    location_match = re.match(
                        r'(\d{2}:)?(?P<value>.*)', location
                    )
                    bldg = '-1'
                    classroom = location_match.group('value')

                else:
                    bldg = location_match.group('building')
                    classroom = location_match.group('classroom')

                ol.add_value(field_name='building', value=bldg)
                ol.add_value(field_name='classroom', value=classroom)
                ol.add_value(field_name='location', value=bldg + '-' + classroom)
                cl.add_value(field_name='occurrences', value=ol.load_item())

            yield(cl.load_item())

        if reached_lower_bound_year:
            # finish scraping one target url. Remove it from list
            logging.log(logging.INFO, self.reach_lower_bound_year_msg.format(self.year_lower_bound))
            logging.log(logging.INFO, "Finish scraping url {}".format(self.current_url))
            self.schools.pop(0)
            if self.schools:
                # continue scraping if list of target schools is not empty
                self.update_school_in_url(self.schools)
                logging.log(logging.INFO, "Start scraping url {}".format(self.current_url))
                yield Request(self.current_url, callback=self.parse, dont_filter=True)
            else:
                raise CloseSpider(self.close_spider_msg)
        else:
            self.increment_page_in_url_by(1)
            yield Request(self.current_url, callback=self.parse, dont_filter=True)

    def period_to_minutes(self, period):
        p_t_m = {
            '1s': 540,
            '1e': 630,
            '2s': 640,
            '2e': 730,
            '3s': 780,
            '3e': 870,
            '4s': 885,
            '4e': 975,
            '5s': 990,
            '5e': 1080,
            '6s': 1095,
            '6e': 1185,
            '7s': 1195,
            '7e': 1285
        }
        try:
            return p_t_m[period]
        except KeyError:
            return -1

    def increment_page_in_url_by(self, increment):
        self.current_page += increment
        self.current_url = customize_url(self.basic_url, self.lang, self.term, self.current_school,
                                         self.results_per_page, self.current_page)

    def update_school_in_url(self, schools):
        self.current_school = schools[0]
        self.current_page = self.start_page
        self.current_url = customize_url(self.basic_url, self.lang, self.term, self.current_school,
                                         self.results_per_page, self.current_page)

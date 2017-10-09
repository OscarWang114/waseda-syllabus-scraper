# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import os

save_path = os.path.dirname(os.path.abspath(__file__))

print(save_path)

if not os.path.exists(save_path):
    os.makedirs(save_path)


class FirstPagePipeline(object):
    def process_item(self, item, spider):
        filename = item['name'] + ".html"
        with open(os.path.join(save_path, filename), 'wb') as f:
            f.write(item['html'])
        return item

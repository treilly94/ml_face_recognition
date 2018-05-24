from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup

import numpy as np
import pandas as pd

from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

import requests
import sys


def get_driver():
    url = "https://www.google.com/flights/explore/#explore;f=LHR,LGW,STN,LTN,LCY,SEN,QQS;t=r-Australia-0x2b2bfd076787c5df%253A0x538267a1955b1352;li=3;lx=5;d=2018-01-09"
    dcap = dict(DesiredCapabilities.PHANTOMJS)
    dcap["phantomjs.page.settings.userAgent"] = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36 OPR/49.0.2725.64")  # This can be found by googeling what is my user agent
    driver = webdriver.PhantomJS(desired_capabilities=dcap, service_args=["--ignore-ssl-errors=true"])
    driver.implicitly_wait(20)
    driver.get(url)

    wait = WebDriverWait(driver, 20)
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.CTPFVNB-w-e")))

    print("Got driver")
    return driver


def get_best_prices(s):
    # Get tags
    best_price_tags = s.find_all("div", "CTPFVNB-w-e")
    # Go through the best price tags and extract the best prices
    best_prices = []
    for tag in best_price_tags:
        best_prices.append(int(tag.text.replace("$", "").replace(",", "")))

    print("Best prices are: %s" % str(best_prices))
    return best_prices


def get_best_heights(s):
    best_height_tags = s.find_all("div", "CTPFVNB-w-f")
    best_heights = []
    for tag in best_height_tags:
        best_heights.append(float(tag.attrs["style"].split("height:")[1].replace("px;", "")))

    print("Best heights are: %s" % str(best_heights))
    return best_heights


def get_city_values(s, pph):
    # Get Cities
    cities = s.find_all("div", "CTPFVNB-v-m")

    # Get the value of each bar
    hlist = []
    for bar in cities[0].find_all("div", "CTPFVNB-w-x"):
        hlist.append(float(bar.attrs["style"].split("height:")[1].replace("px;", "")) * pph)

    print("All values for a city: %s" % str(hlist))
    fares = pd.DataFrame(hlist, columns=["price"])
    return fares


def send_message(message):
    requests.post("https://maker.ifttt.com/trigger/airfare/with/key/bzxVuVYfgLXaGUBWy9NlAl",
                  {"value1": message})

    print("Message sent")


def check_flights():
    # Load driver
    driver = get_driver()

    # Create soup
    s = BeautifulSoup(driver.page_source, "html5lib")

    # Get the best price tags
    best_prices = get_best_prices(s)

    # Check to see if data is loaded correctly
    if len(best_prices) == 0:
        print("Failed to load page data")
        send_message("Read failed")
        sys.exit(0)

    # Get the best height
    best_heights = get_best_heights(s)

    # Find price per pixel
    pph = np.array(best_prices[0]) / np.array(best_heights[0])

    # Get values for city
    fares = get_city_values(s, pph)

    ff = fares.reset_index()

    X = StandardScaler().fit_transform(ff)
    db = DBSCAN(eps=0.5, min_samples=1).fit(X)

    pf = pd.concat([ff, pd.DataFrame(db.labels_, columns=["cluster"])], axis=1)

    rf = pf.groupby("cluster").price.agg(["min", "count"])

    print(rf)

    num_clusters = len(set(db.labels_))

    if num_clusters > 1:
        send_message("There are currently %s clusters" % num_clusters)


if __name__ == "__main__":
    check_flights()
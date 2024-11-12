# Copyright 2019 MaterialEyes
# (see accompanying license files for details).

"""Definition of the ExsclaimTool classes.
This module defines the central objects in the EXSCLAIM!
package. All the model classes are independent of each
other, but they expose the same interface, so they are
interchangeable.
"""
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from . import caption, journal
from .utilities import paths
from .utilities.logging import Printer
import glob
import requests
from bs4 import BeautifulSoup
import shutil
import pathlib
import shutil
import cv2
import numpy as np
from PIL import Image
import numpy as np
from bs4 import BeautifulSoup
from langchain.embeddings import OpenAIEmbeddings
import fitz  # PyMuPDF
import base64 
import io
import hashlib
try:
    from selenium_stealth import stealth
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.common.keys import Keys
except:
    pass

class ExsclaimTool(ABC):
    def __init__(self, search_query):
        self.logger = logging.getLogger(__name__)
        self.initialize_query(search_query)

    def initialize_query(self, search_query):
        """initializes search query as instance attribute

        Args:
            search_query (a dict or path to dict): The Query JSON
        """
        try:
            with open(search_query) as f:
                # Load query file to dict
                self.search_query = json.load(f)
        except Exception:
            self.logger.debug(
                ("Search Query path {} not found. Using it as" " dictionary instead")
            )
            self.search_query = search_query
        # Set up file structure
        base_results_dir = paths.initialize_results_dir(
            self.search_query.get("results_dirs", None)
        )
        self.results_directory = base_results_dir / self.search_query["name"]
        # set up logging / printing
        self.print = "print" in self.search_query.get("logging", [])

    @abstractmethod
    def _load_model(self):
        pass

    @abstractmethod
    def _update_exsclaim(self):
        pass

    @abstractmethod
    def run(self):
        pass

    def display_info(self, info):
        """Display information to the user as the specified in the query

        Args:
            info (str): A string to display (either to stdout, a log file)
        """
        if self.print:
            Printer(info)
        self.logger.info(info)


class JournalScraper(ExsclaimTool):
    """
    JournalScraper object.
    Extract scientific figures from journal articles by passing
    a json-style search query to the run method
    Parameters:
    None
    """

    journals = {
        "acs": journal.ACS,
        "nature": journal.Nature,
        "rsc": journal.RSC,
        "wiley": journal.Wiley,
    }

    def __init__(self, search_query):
        self.logger = logging.getLogger(__name__ + ".JournalScraper")
        self.initialize_query(search_query)
        self.new_articles_visited = set()

    def _load_model(self):
        pass

    def _update_exsclaim(self, exsclaim_dict, article_dict):
        """Update the exsclaim_dict with article_dict contents

        Args:
            exsclaim_dict (dict): An EXSCLAIM JSON
            article_dict (dict):
        Returns:
            exsclaim_dict (dict): EXSCLAIM JSON with article_dict
                contents added.
        """
        exsclaim_dict.update(article_dict)
        return exsclaim_dict

    def _appendJSON(self, filename, exsclaim_json):
        """Commit updates to exsclaim json and update list of scraped articles

        Args:
            filename (string): File in which to store the updated EXSCLAIM JSON
            exsclaim_json (dict): Updated EXSCLAIM JSON
        """
        with open(filename, "w") as f:
            json.dump(exsclaim_json, f, indent=3)
        articles_file = self.results_directory / "_articles"
        with open(articles_file, "a") as f:
            for article in self.new_articles_visited:
                f.write("%s\n" % article.split("/")[-1])

    def run(self, search_query, exsclaim_json={}):
        """Run the JournalScraper to find relevant article figures

        Args:
            search_query (dict): A Search Query JSON to guide search
            exsclaim_json (dict): An EXSCLAIM JSON to store results in
        Returns:
            exsclaim_json (dict): Updated with results of search
        """
        self.display_info("Running Journal Scraper\n")
        # Checks that user inputted journal family has been defined and
        # grabs instantiates an instance of the journal family object
        journal_family_name = search_query["journal_family"]
        if journal_family_name not in self.journals:
            raise NameError(
                "journal family {0} is not defined".format(journal_family_name)
            )
        journal_subclass = self.journals[journal_family_name]
        j_instance = journal_subclass(search_query)

        os.makedirs(self.results_directory, exist_ok=True)
        t0 = time.time()
        counter = 1
        articles = j_instance.get_article_extensions()
        # Extract figures, captions, and metadata from each article
        for article in articles:
            self.display_info(
                ">>> ({0} of {1}) Extracting figures from: ".format(
                    counter, len(articles)
                )
                + article.split("/")[-1]
            )
            try:
                request = j_instance.domain + article
                article_dict = j_instance.get_article_figures(request)
                exsclaim_json = self._update_exsclaim(exsclaim_json, article_dict)
                self.new_articles_visited.add(article)
            except Exception:
                 pass
            #     exception_string = (
            #        "<!> ERROR: An exception occurred in"
            #        " JournalScraper on article: {}".format(article)
            #     )
            #     if self.print:
            #        Printer(exception_string + "\n")
            #     self.logger.exception(exception_string)

            # Save to file every N iterations (to accomodate restart scenarios)
            if counter % 1000 == 0:
                self._appendJSON(
                    self.results_directory / "exsclaim.json", exsclaim_json
                )
            counter += 1

        t1 = time.time()
        self.display_info(
            ">>> Time Elapsed: {0:.2f} sec ({1} articles)\n".format(
                t1 - t0, int(counter - 1)
            )
        )
        self._appendJSON(self.results_directory / "exsclaim.json", exsclaim_json)
        return exsclaim_json


class HTMLScraper(ExsclaimTool):
    """
    HTMLScraper object.
    Extract scientific figures from user provided html articles
    a json-style search query to the run method
    Parameters:
    None
    """

    def __init__(self, search_query, driver=None): # provide the location with the folder with the html files
        self.logger = logging.getLogger(__name__ + ".HTMLScraper")
        self.initialize_query(search_query)
        #self.new_articles_visited = set()
        self.search_query = search_query
        self.open = search_query.get("open", False)
        self.order = search_query.get("order", "relevant")
        self.logger = logging.getLogger(__name__)
        # Set up file structure
        base_results_dir = paths.initialize_results_dir(
            self.search_query.get("results_dirs", None)
        )
        self.results_directory = base_results_dir / self.search_query["name"]
        figures_directory = self.results_directory / "figures"
        os.makedirs(figures_directory, exist_ok=True)

        # initiallize the selenium-stealth
        try:
          options = webdriver.ChromeOptions()
          options.add_argument("--headless")
          options.add_argument("--no-sandbox")
          options.binary_location = "/gpfs/fs1/home/avriza/chrome/opt/google/chrome/google-chrome"
          self.driver = webdriver.Chrome(service=Service('/gpfs/fs1/home/avriza/chromedriver'), options=options)
          stealth(self.driver,
                  languages=["en-US", "en"],
                  vendor="Google Inc.",
                  platform="Win32",
                  webgl_vendor="Intel Inc.",
                  renderer="Intel Iris OpenGL Engine",
                  fix_hairline=True,
                  )
        except:
          self.driver= driver

    def extract_figures_from_html_rsc(self, soup):
        figure_list = soup.find_all("img")
        return figure_list

    def extract_figures_from_html(self, soup):
      figure_list = soup.find_all("figure")
      return figure_list

    def save_figures_rsc(self, filename):

        # Load the HTML file and create a BeautifulSoup object
        with open(filename, "r", encoding="utf-8") as file:
            html_content = file.read()

        soup = BeautifulSoup(html_content, "html.parser")
        url_tag = soup.find("link", rel="canonical")

        if url_tag is not None:
            image_url = url_tag.get("href")
            article_name = image_url.split("/")[-1].split("?")[0]
        else:
          article_name = filename.split(".")[0]


        figures = soup.find_all('div', class_='img-tbl')
        article_json = {}
        figure_number = 1

        for figure in figures:
            try:
                img_url =  figure.find('a')['href']        
            
            except:
                img_tags = figure.find('img')['data-original']
                img_url = 'https://pubs.rsc.org/' + img_tags

            figure_caption=  figure.find('figcaption').get_text(strip=True)


            if img_url is not None:
                self.driver.get(img_url)

            figure_name = article_name + "_fig" + str(figure_number) + ".png"
            figure_path = (
            pathlib.Path("output")  / "figures" / figure_name
            )

            # initialize the figure's json
            figure_json = {
                "title": soup.find("title").get_text(),
                "article_name": article_name,
                "image_url": image_url,
                "figure_name": figure_name,
                "full_caption": figure_caption,
                "figure_path": str(figure_path),
                "master_images": [],
                "article_url":[],
                "license": [],
                "open": [],
                "unassigned": {
                    "master_images": [],
                    "dependent_images": [],
                    "inset_images": [],
                    "subfigure_labels": [],
                    "scale_bar_labels": [],
                    "scale_bar_lines": [],
                    "captions": [],
                },
            }
            # add all results
            article_json[figure_name] = figure_json
            figure_number += 1  # increment figure number
            # Open a file with write binary mode, and write to it
            figures_directory = self.results_directory / "figures"
            figure_path = os.path.join(figures_directory , figure_name)

            with open(figure_path, 'wb') as out_file:
                time.sleep(3)
                self.driver.save_screenshot(figure_path)

                # Load the image
                img = cv2.imread(figure_path, cv2.IMREAD_UNCHANGED)

                # Convert the image to RGBA (just in case the image is in another format)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)

                # Define a 2D filter that will turn black (also shades close to black) pixels to transparent
                low = np.array([0, 0, 0, 0])
                high = np.array([50, 50, 50, 255])

                # Apply the mask (this will turn 'black' pixels to transparent)
                mask = cv2.inRange(img, low, high)
                img[mask > 0] = [0, 0, 0, 0]

                # Convert the image back to PIL format and save the result
                img_pil = Image.fromarray(img)
                img_pil.save(figure_path)
                print('image saved as: ' , figure_path)
        return article_json


    def save_figures_wiley(self, filename):
        # Load the HTML file and create a BeautifulSoup object
        with open(filename, "r", encoding="utf-8") as file:
            html_content = file.read()

        soup = BeautifulSoup(html_content, "html.parser")
        # url_tag = soup.find("link", rel="canonical")
        url_tag = soup.find('meta', attrs={'name': 'pbContext'})
        content = url_tag['content']
        doi_str = [s for s in content.split(';') if 'doi' in s]
        article_doi_list = [doi for doi in doi_str if doi.startswith('article')]
        article_name = article_doi_list[0].split('\\:')[1].split("/")[1]
        # Extract figures from the HTML

        figures = soup.find_all("figure")
        # print(figures)
        article_json = {}
        figure_number = 1

        for figure in figures:

          img = figure.find('img')
          if img:
              img_tags = img['src']
          else:
              source = figure.find('source')
              if source:
                  img_tags = source['srcset']
              else:
                  img_tags = None

          if img_tags is not None:
            img_url = 'https://onlinelibrary.wiley.com' + img_tags
            self.driver.get(img_url)

            # Extract caption
            figure_caption = ""
            caption_tag = figure.find('figcaption')
            if caption_tag:
                # Remove unwanted child elements to avoid redundant text
                for unwanted in caption_tag.find_all(class_="figure-extra"):
                    unwanted.extract()

                # Separate figure title and description
                figure_title = caption_tag.find(class_="figure__title")
                if figure_title:
                    title_text = figure_title.get_text(strip=True) + ':'
                    figure_title.extract()  # remove it from the caption
                else:
                    title_text = ''

                caption = title_text + caption_tag.get_text(strip=True)

            else:
                caption_tag = figure.find('p', class_='caption-style')
                if caption_tag:
                    caption = caption_tag.get_text(strip=True)
                else:
                    caption = None


            # figure_caption = ""
            # caption_tag = figure.find('figcaption')
            # if caption_tag:
            #     # Remove unwanted child elements to avoid redundant text
            #     for unwanted in caption_tag.find_all(class_="figure-extra"):
            #         unwanted.extract()

            #     # Separate figure title and description
            #     figure_title = caption_tag.find(class_="figure__title")
            #     if figure_title:
            #         title_text = figure_title.get_text(strip=True) + '. '
            #         figure_title.extract()  # remove it from the caption
            #     else:
            #         title_text = ''

            #     caption = title_text + caption_tag.get_text(strip=True)

            # else:
            #     caption_tag = figure.find('p', class_='caption-style')
            #     if caption_tag:
            #         caption = caption_tag.get_text(strip=True)
            #     else:
            #         caption = None

            if caption_tag:
              figure_caption += caption_tag.get_text()


              figure_name = article_name + "_fig" + str(figure_number) + ".png"
              figure_path = (
                pathlib.Path("output")  / "figures" / figure_name
              )
              # print('init_figurepath',figure_path )

              # initialize the figure's json
              figure_json = {
                  "title": soup.find("title").get_text(),
                  "article_name": article_name,
                  "image_url": img_url,
                  "figure_name": figure_name,
                  "full_caption": figure_caption,
                  "figure_path": str(figure_path),
                  "master_images": [],
                  "article_url":[],
                  "license": [],
                  "open": [],
                  "unassigned": {
                      "master_images": [],
                      "dependent_images": [],
                      "inset_images": [],
                      "subfigure_labels": [],
                      "scale_bar_labels": [],
                      "scale_bar_lines": [],
                      "captions": [],
                  },
              }
              # add all results
              article_json[figure_name] = figure_json
              figure_number += 1  # increment figure number
              # Open a file with write binary mode, and write to it
              figures_directory = self.results_directory / "figures"
              figure_path = os.path.join(figures_directory , figure_name)
              # print('figurepath',figure_path )

              with open(figure_path, 'wb') as out_file:
                time.sleep(3)
                self.driver.save_screenshot(figure_path)

                # Load the image
                img = cv2.imread(figure_path, cv2.IMREAD_UNCHANGED)

                # Convert the image to RGBA (just in case the image is in another format)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)

                # Define a 2D filter that will turn black (also shades close to black) pixels to transparent
                low = np.array([0, 0, 0, 0])
                high = np.array([50, 50, 50, 255])

                # Apply the mask (this will turn 'black' pixels to transparent)
                mask = cv2.inRange(img, low, high)
                img[mask > 0] = [0, 0, 0, 0]

                # Convert the image back to PIL format and save the result
                img_pil = Image.fromarray(img)
                img_pil.save(figure_path)
                print('image saved as: ' , figure_path)
        return article_json


    def save_figures_acs(self, filename):
    # Load the HTML file and create a BeautifulSoup object
        with open(filename, "r", encoding="utf-8") as file:
            html_content = file.read()

        soup = BeautifulSoup(html_content, "html.parser")
        url_tag = soup.find("link", rel="canonical")

        if url_tag is not None:
            image_url = url_tag.get("href")
            article_name = image_url.split("/")[-1].split("?")[0]
        else:
          article_name = filename.split(".")[0]

        # Extract figures from the HTML
        figures = self.extract_figures_from_html(soup)
        unique_figures = []
        unique_data_indices = set()

        for figure in figures:
          data_index = figure.get('data-index')
          if data_index not in unique_data_indices:
            unique_data_indices.add(data_index)
            unique_figures.append(figure)
        figures = unique_figures

        article_json = {}
        figure_number = 1

        for figure in figures:
              img_tags = figure.find_all("img")
                #print(img_tags)
              for img_tag in img_tags:
                    img_url = img_tag.get("src")
                    img_url = img_url.replace("medium", "large")
                    img_url = img_url.replace("gif", "jpeg")
                    img_url = "https://pubs.acs.org" + img_url
                    captions = figure.find_all("p")

                    figure_caption = ""
                    for caption in captions:
                      if caption is not None:
                        figure_caption += caption.get_text()
                    if img_url is not None:
                      self.driver.get(img_url)
                      #response = requests.get(img_url, stream=True)

                      figure_name = article_name + "_fig" + str(figure_number) + ".png"
                      figure_path = (
                        pathlib.Path("output")  / "figures" / figure_name
                      )

                      # initialize the figure's json
                      figure_json = {
                          "title": soup.find("title").get_text(),
                          "article_name": article_name,
                          "image_url": image_url,
                          "figure_name": figure_name,
                          "full_caption": figure_caption,
                          "figure_path": str(figure_path),
                          "master_images": [],
                          "article_url":[],
                          "license": [],
                          "open": [],
                          "unassigned": {
                              "master_images": [],
                              "dependent_images": [],
                              "inset_images": [],
                              "subfigure_labels": [],
                              "scale_bar_labels": [],
                              "scale_bar_lines": [],
                              "captions": [],
                          },
                      }
                      # add all results
                      article_json[figure_name] = figure_json
                      figure_number += 1  # increment figure number
                      # Open a file with write binary mode, and write to it
                      figures_directory = self.results_directory / "figures"
                      figure_path = os.path.join(figures_directory , figure_name)

                      with open(figure_path, 'wb') as out_file:
                        time.sleep(3)
                        self.driver.save_screenshot(figure_path)

                        # Load the image
                        img = cv2.imread(figure_path, cv2.IMREAD_UNCHANGED)

                        # Convert the image to RGBA (just in case the image is in another format)
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)

                        # Define a 2D filter that will turn black (also shades close to black) pixels to transparent
                        low = np.array([0, 0, 0, 0])
                        high = np.array([50, 50, 50, 255])

                        # Apply the mask (this will turn 'black' pixels to transparent)
                        mask = cv2.inRange(img, low, high)
                        img[mask > 0] = [0, 0, 0, 0]

                        # Convert the image back to PIL format and save the result
                        img_pil = Image.fromarray(img)
                        img_pil.save(figure_path)
                        print('image saved as: ' , figure_path)
        return article_json  # return outside of the for loop to make sure all figures are included


    def save_figures_nature(self, filename):
        # Load the HTML file and create a BeautifulSoup object
        with open(filename, "r", encoding="utf-8") as file:
            html_content = file.read()

        soup = BeautifulSoup(html_content, "html.parser")
        url_tag = soup.find("link", rel="canonical")
        if url_tag is not None:
            image_url = url_tag.get("href")
            article_name = image_url.split("/")[-1].split("?")[0]
        else:
          article_name = filename.split(".")[0]

        # Extract figures from the HTML
        figures = self.extract_figures_from_html(soup)
        article_json = {}
        figure_number = 1

        for figure in figures:
                img_tags = figure.find_all("img")

                for img_tag in img_tags:
                    img_url = img_tag.get("src")
                    captions = figure.find_all("p")

                    figure_caption = ""
                    for caption in captions:
                        figure_caption += caption.get_text()

                    if img_url is not None:
                      response = requests.get('https:'+ img_url, stream=True)



                      figure_name = article_name + "_fig" + str(figure_number) + ".jpg"
                      figure_name = article_name + "_fig" + str(figure_number) + ".jpg"
                      figure_path = (
                        pathlib.Path("output")  / "figures" / figure_name
                      )
                      # print('init_figurepath',figure_path )
                      # initialize the figure's json
                      figure_json = {
                          "title": soup.find("title").get_text(),
                          "article_name": article_name,
                          "image_url": image_url,
                          "figure_name": figure_name,
                          "full_caption": figure_caption,
                          "figure_path": str(figure_path),
                          "master_images": [],
                          "article_url":[],
                          "license": [],
                          "open": [],
                          "unassigned": {
                              "master_images": [],
                              "dependent_images": [],
                              "inset_images": [],
                              "subfigure_labels": [],
                              "scale_bar_labels": [],
                              "scale_bar_lines": [],
                              "captions": [],
                          },
                      }
                      # add all results
                      article_json[figure_name] = figure_json
                      figure_number += 1  # increment figure number
                      # Open a file with write binary mode, and write to it
                      figures_directory = self.results_directory / "figures"
                      figure_path = os.path.join(figures_directory , figure_name)
                      # print('figurepath',figure_path )
                      with open(figure_path, 'wb') as out_file:
                        shutil.copyfileobj(response.raw, out_file)
        return article_json


    def _load_model(self):
        pass

    def get_journal(self, filename):
        keywords = ['acs', 'nature', 'wiley', 'rsc']
        category = None

        with open(filename, "r", encoding="utf-8") as file:
                html_content = file.read()

        soup = BeautifulSoup(html_content, "html.parser")
        # Find all 'a' tags

        for link in soup.find_all('a'):
            url = link.get('href')
            for keyword in keywords:
                if keyword in url:
                    category = keyword
                    break
            if category:
                break
        return category


    def _update_exsclaim(self, exsclaim_dict, article_dict):
        """Update the exsclaim_dict with article_dict contents

        Args:
            exsclaim_dict (dict): An EXSCLAIM JSON
            article_dict (dict):
        Returns:
            exsclaim_dict (dict): EXSCLAIM JSON with article_dict
                contents added.
        """
        exsclaim_dict.update(article_dict)
        return exsclaim_dict

    def _appendJSON(self, filename, exsclaim_json):
        """Commit updates to exsclaim json and update list of scraped articles

        Args:
            filename (string): File in which to store the updated EXSCLAIM JSON
            exsclaim_json (dict): Updated EXSCLAIM JSON
        """
        with open(filename, "w") as f:
            json.dump(exsclaim_json, f, indent=3)
        articles_file = self.results_directory / "_articles"

    def run(self, search_query, exsclaim_json={}):
        """Run the HTMLScraper to retrieve figures from user provided htmls

        Args:
            search_query (dict): A Search Query JSON to guide search
            exsclaim_json (dict): An EXSCLAIM JSON to store results in
        Returns:
            exsclaim_json (dict): Updated with results of search
        """
        self.display_info("Running HTML Scraper\n")

        directory_path = search_query["html_folder"]
        os.makedirs(self.results_directory, exist_ok=True)
        t0 = time.time()
        counter = 1
        articles = glob.glob(os.path.join(directory_path, '*.html'))

        html_directory = self.results_directory / "html"
        os.makedirs(html_directory, exist_ok=True)

        # Extract figures, captions, and metadata from each article
        for article in articles:
            with open(article, "r", encoding="utf-8") as file:
              html_article = file.read()
            soup = BeautifulSoup(html_article, "html.parser")
            url_tag = soup.find("link", rel="canonical")
            # print('url_tag', url_tag)
            if url_tag is not None:
                url = url_tag.get("href")
                with open(html_directory / (url.split("/")[-1] + ".html"), "w", encoding="utf-8") as file:
                  file.write(str(soup))
            else:
              soup = BeautifulSoup(html_article, 'html.parser')
              meta_tag = soup.find('meta', attrs={'name': 'pbContext'})
              content = meta_tag['content']
              doi_str = [s for s in content.split(';') if 'doi' in s]
              article_doi_list = [doi for doi in doi_str if doi.startswith('article')]
              article_name = article_doi_list[0].split('\\:')[1].split("/")[1]
              with open(html_directory / (article_name + ".html"), "w", encoding="utf-8") as file:
                  file.write(str(soup))


            self.display_info(
                ">>> ({0} of {1}) Extracting figures from: ".format(
                    counter, len(articles)
                )
                + article.split("/")[-1]
            )
            journal_name = self.get_journal(article)

            if journal_name == 'nature':
              article_dict = self.save_figures_nature(article)

            if journal_name == 'acs':
              article_dict = self.save_figures_acs(article)

            if journal_name == 'wiley':
              article_dict = self.save_figures_wiley(article)

            if journal_name == 'rsc':
              article_dict = self.save_figures_rsc(article)


            exsclaim_json = self._update_exsclaim(exsclaim_json, article_dict)

            if counter % 1000 == 0:
                self._appendJSON(
                    self.results_directory / "exsclaim.json", exsclaim_json
                )
            counter += 1

        t1 = time.time()
        self.display_info(
            ">>> Time Elapsed: {0:.2f} sec ({1} articles)\n".format(
                t1 - t0, int(counter - 1)
            )
        )
        self._appendJSON(self.results_directory / "exsclaim.json", exsclaim_json)
        return exsclaim_json


class PDFScraper(ExsclaimTool):
    """
    PDFScraper object.
    Extract scientific figures from user provided PDF articles
    a json-style search query to the run method
    Parameters:
    None
    """

    def __init__(self, search_query, driver=None):
        self.logger = logging.getLogger(__name__ + ".PDFScraper")
        self.initialize_query(search_query)
        self.search_query = search_query
        self.api_key = search_query["openai_API"]
        self.open = search_query.get("open", False)
        self.order = search_query.get("order", "relevant")
        self.logger = logging.getLogger(__name__)
        # Set up file structure
        base_results_dir = paths.initialize_results_dir(
            self.search_query.get("results_dirs", None)
        )
        self.results_directory = base_results_dir / self.search_query["name"]
        figures_directory = self.results_directory / "figures"
        os.makedirs(figures_directory, exist_ok=True)

    def encode_image(self,image_path): 
        # Function to encode the image for OpenAI API 
        with open(image_path, "rb") as image_file: 
            return base64.b64encode(image_file.read()).decode('utf-8') 

    def read_figure_captions(self,img_path, api_key ):
        prompt = """The provided image is a page from a literature paper. Please perform the following steps as accurately as possible:
            1. Identify and return in the correct order they are located (the index 0 figure or scheme is located on the top left of the page) in the page the figure name and the full caption that describe the figure or scheme depicted on this page.
            2. If a figure caption or scheme is not found directly above or under the image then do not consider it as an image caption or scheme and return 'N/A.
            2. If a figure doesn't have a directly associated caption found directly above or under the image that starts with 'Fig.' or 'Figure' or 'Scheme' return 'N/A'. 
            3. The figure name or scheme should be found directly above or under the figure and not as part of the main text.
            4. You should not extract image captions from the paper abstract or toc of the paper.
            5. Provide the full caption without splitting it or modifying the content or adding a figure name that is not directly associated with the image.
            
            Follow this example for a page with four figures, where only the three of them have directly associated captions:
            TOC image
            Fig. 6 (A) Cyclic voltammogram of 3 at 0.100 V s−1 on Pt and in situ UV-vis spectral changes during the controlled-potential electrolysis of the solution of 3 at (B)
            −0.80 V (insets a and b show the formation of various isosbestic points within the ranges of 560–580 nm and 680–710 nm, respectively, rather than a well-defined
            single isosbestic point (C) −1.50 V and (D) 0.65 V versus SCE in DMSO/TBAP.
            Scheme 1. Synthetic Approach to Random Copolymerization through Direct Arylation
            Figure 7. (a) Normalized solution UV−vis absorbance spectra of DAT-co-(ran-1,3-DMP) and DAT-co-(reg-1,3-DMP) dissolved in toluene with\nnominal concentrations of 15 μg/mL, 
            and (b) differential scanning calorimetry traces of DAT-co-(ran-1,3-DMP) and DAT-co-(reg-1,3-DMP)\n(second heating cycle).

            Output:
            {"0": "N/A",   
            "1" : "Fig. 6 (A) Cyclic voltammogram of 3 at 0.100 V s−1 on Pt and in situ UV-vis spectral changes during the controlled-potential electrolysis of the solution of 3 at (B)
            −0.80 V (insets a and b show the formation of various isosbestic points within the ranges of 560–580 nm and 680–710 nm, respectively, rather than a well-defined
            single isosbestic point (C) −1.50 V and (D) 0.65 V versus SCE in DMSO/TBAP.",
            "2": "Scheme 1. Synthetic Approach to Random Copolymerization through Direct Arylation",
            "3" : "Figure 7. (a) Normalized solution UV−vis absorbance spectra of DAT-co-(ran-1,3-DMP) and DAT-co-(reg-1,3-DMP) dissolved in toluene with\nnominal concentrations of 15 μg/mL, 
            and (b) differential scanning calorimetry traces of DAT-co-(ran-1,3-DMP) and DAT-co-(reg-1,3-DMP)\n(second heating cycle)."
            }
            """
        base64_image = self.encode_image(img_path) 
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"} 
        payload = { "model": "gpt-4o",  "temperature":0,
                "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, 
                    {"type": "image_url", 
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}], 
                    "max_tokens": 1000 } 
        
        try:         
            response = requests.post("https://api.openai.com/v1/chat/completions", 
                                    headers=headers, json=payload) 
            response.raise_for_status() 
            # print('gpt responce',response.json()['choices'][0]['message']['content'] )
            return response.json()['choices'][0]['message']['content'] 
        
        except Exception as e: 
            print("exception",e) 
            pass


    # Function to extract images from PDF
    # def extract_images_from_pdf(self,pdf_path, output_folder):
    #     pdf_document = fitz.open(pdf_path)
    #     filename = os.path.basename(pdf_path)
    #     article_name = filename.split(".pdf")[0]
    #     print('article_name', article_name)
    #     #  figure_name = f"{os.path.basename(article_name)}_{item['image_filename']}"
    #     image_counter = 0
    #     image_metadata = []
        
    #     # Iterate through each page
    #     for page_num in range(len(pdf_document)):
    #         page = pdf_document.load_page(page_num)
    #         images = page.get_images(full=True)
            
    #         # If images are found
    #         if images:
    #             for img_index, img in enumerate(images):
    #                 xref, smask, w, h = [images[img_index][n] for n in (0, 1, 2, 3)]
    #                 base_image = pdf_document.extract_image(xref)
    #                 image_bytes = base_image["image"]
    #                 image_ext = base_image["ext"]
    #                 image_filename = f"{article_name}_page_{page_num+1}_img_{img_index+1}.{image_ext}"
    #                 # output = f'{page.number + 1:03}-{xref + 1:05}'

    #                 if smask:
    #                     # Handle the image mask
    #                     mask = fitz.Pixmap(pdf_document, smask)
    #                     if (mask.width != w) or (mask.height != h):
    #                         mask = fitz.Pixmap(mask, w, h, None)
    #                     image = fitz.Pixmap(pdf_document, xref)
    #                     image = fitz.Pixmap(image, mask)
    #                     image = fitz.Pixmap(fitz.csRGB, image) 
    #                     output = f'{os.path.join(output_folder, image_filename)}'
    #                     image.save(output)

    #                 else:
    #                     image = fitz.Pixmap(pdf_document, xref)

    #                     if image.alpha:
    #                         output = f'{os.path.join(output_folder, image_filename)}'
    #                         image.save(output)
    #                     else:
    #                         output = f'{os.path.join(output_folder, image_filename)}' 
    #                         image = fitz.Pixmap(fitz.csRGB, image) 
    #                         image.save(output)

    #                 image_metadata.append({
    #                     "page_num": page_num + 1,
    #                     "image_filename": image_filename
    #                 })
    #                 image_counter += 1

    #     return image_metadata
    
    # def extract_images_from_pdf(self, pdf_path, output_folder, logo_hashes):
    #     pdf_document = fitz.open(pdf_path)
    #     image_counter = 0
    #     image_metadata = []

    #     # Ensure output folder exists
    #     os.makedirs(output_folder, exist_ok=True)

    #     # Iterate through each page
    #     for page_num in range(len(pdf_document)):
    #         page = pdf_document.load_page(page_num)
    #         print(f"Processing page {page_num+1}")

    #         # Get images on the page with detailed info
    #         images = page.get_images(full=True)
    #         print(f"Found {len(images)} images on page {page_num+1}")

    #         # Collect images with their positions
    #         image_list = []

    #         for img in images:
    #             xref = img[0]
    #             # Get the rectangles where this image is used
    #             rects = page.get_image_rects(xref)
    #             if rects:
    #                 for rect in rects:
    #                     image_list.append({
    #                         "xref": xref,
    #                         "rect": rect
    #                     })
    #             else:
    #                 print(f"No rectangles found for image xref {xref} on page {page_num+1}")

    #         if not image_list:
    #             print(f"No images with positions found on page {page_num+1}")
    #             continue

    #         # Sort images from top to bottom based on their vertical position
    #         image_list.sort(key=lambda img: img["rect"].y1, reverse=False)

    #         # Save images in the sorted order
    #         for img_index, img in enumerate(image_list):
    #             xref = img["xref"]
    #             rect = img["rect"]

    #             try:
    #                 pix = fitz.Pixmap(pdf_document, xref)

    #                 # Skip images with NULL colorspace
    #                 if pix.colorspace is None:
    #                     print(f"Skipping image xref {xref} on page {page_num+1} due to NULL colorspace")
    #                     continue

    #                 image_hash = hashlib.md5(pix.samples).hexdigest()
    #                 if image_hash in logo_hashes:
    #                     print(f"Skipping logo image xref {xref} on page {page_num+1}")
    #                     continue

    #                 # Skip small images (e.g., logos) based on size
    #                 image_width = pix.width
    #                 image_height = pix.height
    #                 if image_width <= 100 and image_height <= 100:
    #                     print(f"Skipping small image xref {xref} on page {page_num+1} (likely a logo)")
    #                     continue

    #                 # Convert CMYK and other unsupported colorspaces to RGB
    #                 if pix.colorspace.name == 'DeviceCMYK' or pix.colorspace.n > 3:
    #                     print(f"Converting image xref {xref} from colorspace {pix.colorspace.name} to RGB")
    #                     pix = fitz.Pixmap(fitz.csRGB, pix)

    #                 # Convert grayscale images to RGB
    #                 elif pix.colorspace.n == 1:
    #                     print(f"Converting grayscale image xref {xref} to RGB")
    #                     pix = fitz.Pixmap(fitz.csRGB, pix)

    #                 # Save the image as PNG
    #                 image_filename = f"page_{page_num+1}_img_{img_index+1}.png"
    #                 image_output_path = os.path.join(output_folder, image_filename)
    #                 pix.save(image_output_path)
    #                 print(f"Saved image {image_filename}")
    #                 pix = None  # Free resources

    #                 image_metadata.append({
    #                     "page_num": page_num + 1,
    #                     "image_index": img_index + 1,
    #                     "image_filename": image_filename,
    #                     "rect": [rect.x0, rect.y0, rect.x1, rect.y1]
    #                 })
    #                 image_counter += 1

    #             except Exception as e:
    #                 print(f"Error processing image xref {xref} on page {page_num+1}: {e}")

    #     if image_counter == 0:
    #         print("No images were saved.")
    #     else:
    #         print(f"Total images saved: {image_counter}")

    #     return image_metadata

    def extract_images_from_pdf(self, pdf_path, output_folder, logo_hashes):
        pdf_document = fitz.open(pdf_path)
        image_counter = 0
        image_metadata = []

        # Ensure output folder exists
        os.makedirs(output_folder, exist_ok=True)

        # Iterate through each page
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            print(f"Processing page {page_num+1}")

            # Get images on the page with detailed info
            images = page.get_images(full=True)
            print(f"Found {len(images)} images on page {page_num+1}")

            # Collect images with their positions
            image_list = []

            for img in images:
                xref = img[0]
                # Get the rectangles where this image is used
                rects = page.get_image_rects(xref)
                if rects:
                    for rect in rects:
                        image_list.append({
                            "xref": xref,
                            "rect": rect
                        })
                else:
                    print(f"No rectangles found for image xref {xref} on page {page_num+1}")

            if not image_list:
                print(f"No images with positions found on page {page_num+1}")
                continue

            # Get the page width to determine left and right halves
            page_width = page.rect.width

            # Classify images into left and right based on x_center
            left_images = []
            right_images = []

            for img in image_list:
                rect = img["rect"]
                x_center = (rect.x0 + rect.x1) / 2
                y_top = rect.y1  # Top edge of the image
                img["x_center"] = x_center
                img["y_top"] = y_top

                if x_center < page_width / 2:
                    left_images.append(img)
                else:
                    right_images.append(img)

            # Sort images in each group from top to bottom (higher y to lower y)
            left_images.sort(key=lambda img: img["y_top"], reverse=True)
            right_images.sort(key=lambda img: img["y_top"], reverse=False)

            # Combine the lists: left images first, then right images
            sorted_images = left_images + right_images

            # Save images in the sorted order
            for img_index, img in enumerate(sorted_images):
                xref = img["xref"]
                rect = img["rect"]

                try:
                    pix = fitz.Pixmap(pdf_document, xref)

                    # Skip images with NULL colorspace
                    if pix.colorspace is None:
                        print(f"Skipping image xref {xref} on page {page_num+1} due to NULL colorspace")
                        continue

                    image_hash = hashlib.md5(pix.samples).hexdigest()
                    if image_hash in logo_hashes:
                        print(f"Skipping logo image xref {xref} on page {page_num+1}")
                        continue

                    # Skip small images (e.g., logos) based on size
                    image_width = pix.width
                    image_height = pix.height
                    if image_width <= 100 and image_height <= 100:
                        print(f"Skipping small image xref {xref} on page {page_num+1} (likely a logo)")
                        continue

                    # Convert CMYK and other unsupported colorspaces to RGB
                    if pix.colorspace.name == 'DeviceCMYK' or pix.n > 4:
                        print(f"Converting image xref {xref} from colorspace {pix.colorspace.name} to RGB")
                        pix = fitz.Pixmap(fitz.csRGB, pix)

                    # Convert grayscale images to RGB
                    elif pix.colorspace.n == 1:
                        print(f"Converting grayscale image xref {xref} to RGB")
                        pix = fitz.Pixmap(fitz.csRGB, pix)

                    # Save the image as PNG
                    image_filename = f"page_{page_num+1}_img_{img_index+1}.png"
                    image_output_path = os.path.join(output_folder, image_filename)
                    pix.save(image_output_path)
                    print(f"Saved image {image_filename}")
                    pix = None  # Free resources

                    image_metadata.append({
                        "page_num": page_num + 1,
                        "image_index": img_index + 1,
                        "image_filename": image_filename,
                        "rect": [rect.x0, rect.y0, rect.x1, rect.y1]
                    })
                    image_counter += 1

                except Exception as e:
                    print(f"Error processing image xref {xref} on page {page_num+1}: {e}")

        if image_counter == 0:
            print("No images were saved.")
        else:
            print(f"Total images saved: {image_counter}")

        return image_metadata

    def extract_captions_from_pdf(self, pdf_path, dpi=300):
        captions = {}
        pdf_document = fitz.open(pdf_path)
        for page_num, page in enumerate(pdf_document):
            # Extract text from the page
            page_text = page.get_text()
            # Check if the page is Table of Contents
            # if 'table of contents' in page_text.lower() or 'contents' in page_text.lower():
            #     print(f"Skipping page {page_num + 1} as it appears to be Table of Contents.")
            #     continue

            scale_factor = dpi / 72
            pix = page.get_pixmap(matrix=fitz.Matrix(scale_factor, scale_factor))
            img_bytes = pix.tobytes()
            image = Image.open(io.BytesIO(img_bytes))
            image.save('pdf.png')
            extracted_data_str = self.read_figure_captions('pdf.png', self.api_key)
            json_start = extracted_data_str.find('{')
            json_end = extracted_data_str.rfind('}')

            if json_start != -1 and json_end != -1:
                # Extract the valid JSON part
                extracted_data_str = extracted_data_str[json_start:json_end + 1]
            else:
                print(f"Error: No valid JSON found in response for page {page_num + 1}. Skipping.")
                continue

            try:
                # Parse the cleaned string as JSON
                extracted_data = json.loads(extracted_data_str)

                if isinstance(extracted_data, dict):
                    page_captions = extracted_data.values()
                    page_captions = [" ".join(caption) if isinstance(caption, list) else caption for caption in page_captions]
                else:
                    page_captions = []
                
                captions[page_num + 1] = page_captions
            
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON for page {page_num + 1}: {e}")
        
        return captions


    # Function to match captions with images
    def match_images_with_captions(self, image_metadata, captions):
        for img_meta in image_metadata:
            page_num = img_meta['page_num']
            
            # Convert dict_values to list for indexing
            page_captions = list(captions.get(page_num, []))  # Convert dict_values to list
            
            # Assign captions in order if there are captions available
            if page_captions:
                img_index = image_metadata.index(img_meta) % len(page_captions)
                img_meta['captions'] = page_captions[img_index]
            else:
                img_meta['captions'] = "N/A"  # Assign "N/A" if no captions are found
        
        return image_metadata

    # Main function
    def process_pdf(self,pdf_path, output_folder, logo_hashes=None):
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        # Step 1: Extract images from PDF
        image_metadata = self.extract_images_from_pdf(pdf_path, output_folder, logo_hashes)
        
        # Step 2: Extract captions from PDF
        captions = self.extract_captions_from_pdf(pdf_path)
        
        # Step 3: Match images with captions
        matched_metadata = self.match_images_with_captions(image_metadata, captions)
        
        return matched_metadata


    def extract_title_from_pdf(self, pdf_path):
        pdf_document = fitz.open(pdf_path)
        
        # Get the title from metadata
        metadata = pdf_document.metadata
        title = metadata.get('title', '')
        
        # If no title in metadata, try to extrct from text in the first page
        if not title:
            first_page = pdf_document.load_page(0)
            first_page_text = first_page.get_text("text")
            first_lines = first_page_text.splitlines()[:5]
            title = " ".join(first_lines).strip()        
        return title


    def save_figures_pdf(self, filename):

        article_name = filename.split(".pdf")[0]
        #  figure_name = f"{os.path.basename(article_name)}_{item['image_filename']}"
        output_folder = self.results_directory / "figures" #/"all_figures"
        logo_hashes = set(['a6030f1bba4aa390c453d28c14a58c1d', '4c01d3acab441ccc10381b6a62afa238', '7caa14a242ee374229c8d081852e1b57', '91623e2a4e1255c78ca3c88aae5ff690'])   
        image_caption_metadata = self.process_pdf(filename, output_folder, logo_hashes)
        title = self.extract_title_from_pdf(filename)
        article_json = {}
        figure_number = 1
                
        for item in image_caption_metadata:
            valid_captions = [caption for caption in item['captions'] if caption != 'N/A' and caption.strip() != '']
            
            if valid_captions:
                print(f"Image: {item['image_filename']}, Page: {item['page_num']}, Captions: {item['captions']}")

                figure_name = item['image_filename'] #f"{os.path.basename(article_name)}_{item['image_filename']}"
                figure_path = (
                pathlib.Path("output")  / "figures" / figure_name
                )
                # initialize the figure's json
                figure_json = {
                    "title": title,
                    "article_name": article_name,
                    "image_url": [],
                    "figure_name": figure_name,
                    "full_caption": item['captions'],
                    "figure_path": str(figure_path),
                    "master_images": [],
                    "article_url":[],
                    "license": [],
                    "open": [],
                    "unassigned": {
                        "master_images": [],
                        "dependent_images": [],
                        "inset_images": [],
                        "subfigure_labels": [],
                        "scale_bar_labels": [],
                        "scale_bar_lines": [],
                        "captions": [],
                    },
                }
                # add all results
                article_json[figure_name] = figure_json
                figure_number += 1
                figures_directory = self.results_directory / "figures"
                figure_path = os.path.join(figures_directory , figure_name)
                figure_init_path = os.path.join(output_folder , figure_name)
                shutil.move(figure_init_path, figure_path)
        return article_json


    def _load_model(self):
        pass

    def _update_exsclaim(self, exsclaim_dict, article_dict):
        """Update the exsclaim_dict with article_dict contents

        Args:
            exsclaim_dict (dict): An EXSCLAIM JSON
            article_dict (dict):
        Returns:
            exsclaim_dict (dict): EXSCLAIM JSON with article_dict
                contents added.
        """
        exsclaim_dict.update(article_dict)
        return exsclaim_dict

    def _appendJSON(self, filename, exsclaim_json):
        """Commit updates to exsclaim json and update list of scraped articles

        Args:
            filename (string): File in which to store the updated EXSCLAIM JSON
            exsclaim_json (dict): Updated EXSCLAIM JSON
        """
        with open(filename, "w") as f:
            json.dump(exsclaim_json, f, indent=3)
        articles_file = self.results_directory / "_articles"


    def extract_text_from_pdf(self, pdf_path):
        "Extracts text from a PDF file and saves it a txt"
        pdf_document = fitz.open(pdf_path)
        pdf_text = ""
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            pdf_text += page.get_text() + "\n"        
        return pdf_text

    def run(self, search_query, exsclaim_json={}):
        """Run the HTMLScraper to retrieve figures from user provided htmls

        Args:
            search_query (dict): A Search Query JSON to guide search
            exsclaim_json (dict): An EXSCLAIM JSON to store results in
        Returns:
            exsclaim_json (dict): Updated with results of search
        """
        self.display_info("Running PDF Scraper\n")

        directory_path = search_query["pdf_folder"]
        os.makedirs(self.results_directory, exist_ok=True)
        t0 = time.time()
        counter = 1
        articles = glob.glob(os.path.join(directory_path, '*.pdf'))
        pdf_directory = self.results_directory / "pdf"
        os.makedirs(pdf_directory, exist_ok=True)
        print('articles', articles)

        for article in articles:
            self.display_info(
                ">>> ({0} of {1}) Extracting figures from: ".format(
                    counter, len(articles)
                )
                + article.split("/")[-1]
            )

            pdf_text = self.extract_text_from_pdf(article)
            
            file_path = os.path.join(pdf_directory, f"{os.path.basename(article).split('.pdf')[0]}.txt")
            # print('file_path')
            # print(f"{os.path.basename(article).split('.pdf')[0]}.txt")
            # print(pdf_directory)

            with open(file_path, 'w', encoding='utf-8') as text_file:
                text_file.write(pdf_text)

            article_dict = self.save_figures_pdf(article)

            exsclaim_json = self._update_exsclaim(exsclaim_json, article_dict)

            if counter % 1000 == 0:
                self._appendJSON(
                    self.results_directory / "exsclaim.json", exsclaim_json
                )
            counter += 1

        t1 = time.time()
        self.display_info(
            ">>> Time Elapsed: {0:.2f} sec ({1} articles)\n".format(
                t1 - t0, int(counter - 1)
            )
        )
        self._appendJSON(self.results_directory / "exsclaim.json", exsclaim_json)
        # exsclaim_json = self.clean_json_file(exsclaim_json)
        return exsclaim_json


class CaptionDistributor(ExsclaimTool):
    """
    CaptionDistributor object.
    Distribute subfigure caption chunks from full figure captions
    in an exsclaim_dict using custom caption nlp tools
    Parameters:
    model_path: str
        Absolute path to caption nlp model
    """

    def __init__(self, search_query={}):
        super().__init__(search_query)
        self.logger = logging.getLogger(__name__ + ".CaptionDistributor")
        self.model_path = ""

    def _load_model(self):
        if "" in self.model_path:
            self.model_path = os.path.dirname(__file__) + "/captions/models/"
        return caption.load_models(self.model_path)
    
    
    def _clean_json_file(self, json_file):
        """
        Function to remove elements where the caption is 'N/A'
        """
        data = json_file 

        for key in list(data.keys()):
            caption = data[key]["full_caption"]
            if caption == "N/A":
                del data[key]
        
        return data
        

    def _update_exsclaim(self,search_query,  exsclaim_dict, figure_name, delimiter, caption_dict):
        from tools.exsclaim.exsclaim import caption
        llm = search_query["llm"]
        api = search_query["openai_API"]
        exsclaim_dict[figure_name]["caption_delimiter"] = delimiter
        html_filename = exsclaim_dict[figure_name]["article_name"]
        embeddings = OpenAIEmbeddings( openai_api_key=api)
        file_path = os.path.join("tools", "exsclaim", "output", search_query["name"], "html", f'{html_filename}.html')

        # loader = UnstructuredHTMLLoader(file_path)
        # documents = loader.load()
        #loader = UnstructuredHTMLLoader(os.pathjoin("exsclaim", "output", exsclaim_dict["name"], "html", f'{html_filename}.html'))
        for label in caption_dict.keys():
            query = (exsclaim_dict[figure_name]["figure_name"].split('.')[0]).split('_')[-1] + label + " " + caption_dict[label]
            print('query', query)
            master_image = {
                "label": label,
                "description": caption_dict[label],
                "keywords": caption.safe_summarize_caption(query , api, llm).split(', ') ,
                # "context": caption.get_context(query, documents,embeddings),
                # "general": caption.get_keywords(caption.get_context(query, documents,embeddings), api, llm).split(', '),
            }
            exsclaim_dict[figure_name]["unassigned"]["captions"].append(master_image)
        return exsclaim_dict

    def _appendJSON(self, exsclaim_json, captions_distributed):
        """Commit updates to EXSCLAIM JSON and updates list of ed figures

        Args:
            results_directory (string): Path to results directory
            exsclaim_json (dict): Updated EXSCLAIM JSON
            figures_separated (set): Figures which have already been separated
        """
        with open(self.results_directory / "exsclaim.json", "w") as f:
            json.dump(exsclaim_json, f, indent=3)
        try:    
            with open(self.results_directory / "_captions", "a+") as f:
                for figure in captions_distributed:
                    f.write("%s\n" % figure.split("/")[-1])
        except:
            with open(self.results_directory / "_captions", "a+", encoding='utf-8') as f:
                    f.write("%s\n" % figure.split("/")[-1])

    def run(self, search_query, exsclaim_json):
        """Run the CaptionDistributor to distribute subfigure captions

        Args:
            search_query (dict): A Search Query JSON to guide search
            exsclaim_json (dict): An EXSCLAIM JSON to store results in
        Returns:
            exsclaim_json (dict): Updated with results of search
        """
        # exsclaim_json = self._clean_json_file(exsclaim_json)
        self.display_info("Running Caption Distributor\n")
        os.makedirs(self.results_directory, exist_ok=True)
        t0 = time.time()

        # List captions that have already been distributed
        captions_file = self.results_directory / "_captions"
        if os.path.isfile(captions_file):
            with open(captions_file, "r") as f:
                contents = f.readlines()
            captions_distributed = {f.strip() for f in contents}
        else:
            captions_distributed = set()
        new_captions_distributed = set()

        figures = [
            exsclaim_json[figure]["figure_name"]
            for figure in exsclaim_json
            if exsclaim_json[figure]["figure_name"] not in captions_distributed
        ]
        counter = 1
        for figure_name in figures:
            self.display_info(
                ">>> ({0} of {1}) ".format(counter, +len(figures))
                + "Parsing captions from: "
                + figure_name
            )
            try:
                caption_text = exsclaim_json[figure_name]["full_caption"]
                print('full caption',caption_text)
                #delimiter = caption.find_subfigure_delimiter(model, caption_text)
                delimiter = 0
                llm = search_query["llm"]
                #print('llm', llm)
                api = search_query["openai_API"]
                #print('api',api)
                caption_dict = caption.separate_captions(caption_text, api, llm)
                print('full caption dict', caption_dict )
                exsclaim_json = self._update_exsclaim(search_query,
                    exsclaim_json, figure_name, delimiter, caption_dict
                )
                new_captions_distributed.add(figure_name)
            except Exception:
                #pass
                if self.print:
                    Printer(
                        (
                            "<!> ERROR: An exception occurred in"
                            " CaptionDistributor on figue: {}".format(figure_name)
                        )
                    )
                self.logger.exception(
                    (
                        "<!> ERROR: An exception occurred in"
                        " CaptionDistributor on figue: {}".format(figure_name)
                    )
                )
            # Save to file every N iterations (to accomodate restart scenarios)
            if counter % 100 == 0:
                self._appendJSON(exsclaim_json, new_captions_distributed)
                new_captions_distributed = set()
            counter += 1

        t1 = time.time()
        self.display_info(
            ">>> Time Elapsed: {0:.2f} sec ({1} captions)\n".format(
                t1 - t0, int(counter - 1)
            )
        )
        self._appendJSON(exsclaim_json, new_captions_distributed)
        return exsclaim_json
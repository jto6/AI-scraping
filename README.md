# AI-scraping
scripts to aid in collecting data to feed to AI models

It contains the following scripts
* sitemap.py - This will download the sitemap of a website and generate a list of URLs on the site
* process_sitemap.py - This will read in a .txt file of URLs and generate a combined .pdf file.  You would typically get the .txt file from sitemap.py, with possibly some breaking up of sitemap.py output into separate files for each domain, if it is a large web site.
* url-crawler-pdf.py - give a website, it will visit all pages reachable from it and within the same domain and directory, and generate a combined pdf of those visited pages


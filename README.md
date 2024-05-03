# ner-demo

## Introduction
This project aims to allow users to search for a law firm and get: i) a list of [Above the Law](https://abovethelaw.com/) articles mentioning that firm, and ii) a list of partners and other employees associated with that firm.

To do that, roughly 8,600 articles were obtained from Above the Law. As described below, two separate named-entity recognition and relation extraction pipelines were then applied to this dataset. Each of these pipelines generated a knowledge-graph database showing relationships between firms, employees, and articles. Finally, these databases were exposed through a (very) simple [web interface](http://ner-demo.xyz/).

This README contains an overview of the code base as well as a brief discussion of modeling results and suggested next steps.

## Table of Contents
* [Introduction](#introduction)
* [Table of Contents](#table-of-contents)
* [Database](#database)
* [Predictive Models](#predictive-models)
  + [Flair + Babel based](#flair--babel-based)
  + [LLaMA based](#llama-based)
* [Text Processing + Data Ingestion](#text-processing--data-ingestion)
  + [Article Scraping + Processing](#article-scraping--processing)
  + [Text Filtering](#text-filtering)
* [Web Server](#web-server)
* [Next steps](#next-steps)



## Database
In order to best capture relationships between firms, partners, and articles, [a knowledge-graph database](https://github.com/bensetel/ner-takehome/blob/main/src/database.py) is used to store model outputs. Specifically, a self-hosted [Neo4j](https://github.com/neo4j/neo4j) database was chosen, due to its native knowledge graph support and visualization tools.

Our database has three fundamental types of objects: Firms, People, and Articles. Each time a firm or person is identified in an article, the following objects and relations are either created or updated:

	* Firm -> :Mentioned_In -> Article
	* Article -> :Mentions -> Firm
	* Employee -> :Mentioned_In -> Article
	* Article -> :Mentions -> Employee
	* Employee -> :Works_For -> Firm
	* Firm -> :Employs -> Employee

In addition to these relationships, each Firm has at least a Name field, and many have websites, headquarters locations and headcounts. Each Employee has a Name, and each Article has a Title and a URL.

Annoyingly, the community edition of Neo4j only supports one database per server. As a result, separate *servers* are maintained for the outputs of the LLaMA and Flair/Babel models[^1], instead of just separate databases on the same server.

## Predictive Models

Two NER + relation-extraction models are available. The first uses [Flair](https://flairnlp.github.io/) for NER, then passes the tagged sentence to [REBEL](https://github.com/Babelscape/rebel) for Relation Extraction. This represents a fairly conventional approach, using task-specific NLP models. The second model is based on Meta's [LLaMA 3](https://llama.meta.com/llama3/). This approach hosts the 8B-parameter version of LLaMA locally, and prompts it by asking it to extract a knowledge graph before sending it the text of the article. While not a task-specific model, LLaMA demonstrated substantial understanding of the request and produced very good results. Several attempts at fine-tuning were explored, but none produced better results than the out-of-the-box models. With more time and a larger corpus, however, fine-tuning could probably improve both models.

Note: a fair amount of text processsing, both to extract article text and to filter/check model outputs, is applied. Please see the [text processing section](#Text-Processing--Data-Ingestion) for details.

### [Flair + Babel based](https://github.com/bensetel/ner-takehome/blob/main/src/babel_flair_model.py):
In this approach, we feed the article text into Flair's [NER-Large](https://huggingface.co/flair/ner-english-large) model for NER tagging. This model does a reasonably good job of tagging law firms with the "ORG" label. It struggles a bit at tagging people with the 'PER' label. This may be in part because law firm names *contain* people's names (e.g. "Kirkland & Ellis" is just two last names), making it fairly difficult to distinguish a person's name from a firm's name.

When Flair identifies that a firm is mentioned in an article, that article is added to our [database](#Database), along with two relationships: one pointing from the Firm object to the Article object with the ":Mentioned In" relationship, and another from the Article to the Firm with the ":Mentions" relationship.


In addition to populating our database, we create a list of the firms and people identified by Flair to cross-check against Babel's relationship predictions. Babel sometimes hallucinates, so it is useful to check that any relationship it identifies actually involves entities mentioned in the article.

The text tagged by Flair's model is then fed into Babel's [REBEL](https://github.com/Babelscape/rebel) model. This model attempts to perform relation extraction on the tagged text, to identify employees of firms mentioned in articles. Unfortunately, despite [high performance](https://paperswithcode.com/sota/relation-extraction-on-nyt) on the [New York Times Annotated Corpus](https://paperswithcode.com/dataset/new-york-times-annotated-corpus), the model struggled to identify firm employees. As noted above, this may be in part because the names of the law firms are themselves people's names. When Babel identifies a relationship between an entity tagged as an 'ORG' by Flair and one tagged as 'PER', both entities are added to (or updated if they already exist) our database, with ":Employs" and ":Works_For" relationships between them.

Overall, this approach did pretty well at NER but struggled a bit with relation extraction. It was pretty fast, however. Inference across our ~8,600 article dataset took less than 8 hours (could have been substantially less - I ran it overnight and it finished before I woke up).


### [LLaMA based](https://github.com/bensetel/ner-takehome/blob/main/src/llama_model.py):

In this approach, we use [LLaMA 3](https://llama.meta.com/llama3/), an open-access (including for commercial use) large language model developed by Meta for both entity recognition and relation extraction. The pre-trained 8B parameter version of the model (which occupies roughly ~16GB of disk space) is deployed on a VM with an [NVIDIA L40S](https://www.nvidia.com/en-us/data-center/l40s/) GPU attached.

The model is loaded as a [HuggingFace Text Generation Pipeline](https://huggingface.co/docs/transformers/en/main_classes/pipelines#transformers.TextGenerationPipeline). For each article, the model is provided with two input prompts. The first instructs to perform NER and relation extraction on the text and to format its output as:

```
+ Firm 1 Name
  - Employee 1 name
  - Employee 2 name
  - Employee 3 name
  ...

+ Firm 2 Name
  - Employee 1 name
  - Employee 2 name
...
```
Several variations of this prompt were tried, and they had a noticeable impact on performance (both speed and quality). The model took *much* longer to analyze each article when even slight variations to the formatting instructions were tried. Also, telling the model that it was okay if no firms or employees could be identified in a given article significantly improved both inference time and quality.


The second prompt provides the text of the article. The model then outputs a list of firms it has identified in the text, along with any employees of those firms that it has identified. Each firm and employee identified is then added to the database.

Overall, LLaMA did quite well with this task. Inference across our ~8,600 article dataset took roughly 21 hours (a little less than 9 seconds per article). The most common mistakes it made were identifying other types of organizations as law firms (e.g. Thomson Reuters, the New York Times, etc.), and assinging people mentioned in an article to the wrong organization (and in particular, saying that the author of the article worked for one of the firms mentioned).


## Text Processing + Data Ingestion

### [Article Processing]
<!-- [UseScraper](https://usescraper.com/)'s crawler feature did not work on Above The Law. Instead, I wrote and ran [my own small scraper](https://github.com/bensetel/ner-takehome/blob/main/src/scraping/scrape_url_names.py) to populate a list of article urls, and then [called UseScraper's scrape function](https://github.com/bensetel/ner-takehome/blob/main/src/scraping/scrape_article_content.py) on each url. The list of urls is stored as a simple text file.  -->

The articles are added to a Pandas dataframe with both their text and metadata, and stored as .csv files. To run articles through the model, the entire dataset is loaded into one Pandas DataFrame and [some simple preprocessing](https://github.com/bensetel/ner-takehome/blob/main/src/csv_processing.py) is then applied. The article text is extracted from the surrounding webpage content using some very simple pattern matching on site elements. Links and advertisements are removed, and the article title and url are extracted from the metadata. A dataframe containing this processed article text, url, and title for every article is then passed to the model. In total, 8,664 articles were succesfully added to our dataset and provided to the models.


### Text Filtering
Both models' output was subject to some [simple text filtering](https://github.com/bensetel/ner-takehome/blob/main/src/string_filters.py). Identified firm and person names were checked against a list of bad keywords and names of Above The Law staff writers (both models often thought that article authors were firm employees). People's names were also subject to simple regex filter. As discussed [above](#Next-Steps) additional filtering could probably significantly improve model performance.




## [Web Server](https://github.com/bensetel/ner-takehome/tree/main/web_server/web_server)
A very simple website is maintained at [ner-demo.xyz](http://ner-demo.xyz/) to expose a search function for each of our two databases. We use a very simple tech stack for this: Nginx -> Gunicorn -> Django (on Ubuntu, but could pretty much be any unix-like). First, the user selects a database, and then enters a law firm name. We retrieve all articles and people with connected by any edge to that firm in our knowledge graph.

We also include links to Neo4j's database interface, mostly so that users with database logins can use Neo4j's graph visualization tools. To play around with the LLaMA-generated graph, go [here](http://163.74.91.141:7474/browser/).

Login is:

```
user: "neo4j"
password: "pleasedonthackme123"
```

Try entering the following queries to get firms/people/articles, then double-click on a node to see its connectons.

```
MATCH (f:Firm) RETURN f;

MATCH (p:Person) RETURN p;

MATCH (a:Article) RETURN a;
```

## Next steps
### Models
Both of these models could be significantly improved with additional filtering. I think the following specific steps would help:

- Create a definitive list of firms:

  * The legal world is relatively small, and a comprehensive list of all law firms of interest would probably not be that hard to create independently of these models. For instance, the top 250 firms by headcount in the US are listed [here](http://www.lawadmin.com/top250.asp). Any predictions our model makes could then be checked against this list, to ensure that the output is discussing a real law firm.

- Cross-check employees against state bar profiles and/or firm websites:

  * Every state bar in the United States has an attorney lookup tool, to help the public ensure that they are dealing with a legitamtely licensed attorney. (e.g. [New York](https://iapps.courts.state.ny.us/attorneyservices/search?1), [California](https://apps.calbar.ca.gov/attorney/LicenseeSearch/QuickSearch); [my California profile](https://apps.calbar.ca.gov/attorney/Licensee/Detail/319289)). Generally, an attorney profile will list at least a business address. State profiles for each employee identified by our model could be checked, to ensure that the person i) actually exists and ii) actually works for the identified firm.

  * (Almost) every law firm has a firm website that lists all of its attorneys (e.g. [Davis Polk](https://www.davispolk.com/lawyers?lawyer_search_en%5BrefinementList%5D%5Bjob_title%5D%5B0%5D=Partner)). These firm website profiles tend to be towards the top of Google search results. This suggests two approaches. First, we could just try to scrape every firm website and cross-check any idenitified employees against this list (and/or build out our relationship database this way). Second, we could google any name predicted by the model and check whether a corresponding firm profile is within the top few results.

### Database
The database could also be significantly improved by using these same filtering methods to remove Firm and Person nodes that do not meet the filter criteria above.

Another *crucial* next step would be to de-duplicate Firm (and to a lesser extent Person) nodes. The same firm may be known by several aliases (e.g. "Davis Polk & Wardwell", "Davis Polk", "DPW", "Davis Polk & Wardwell LLP", or "Sullivan & Cromwell", "Sullcrom", etc). Constructing a list of firm aliases and joining Firm nodes would be my immediate next step if I were to continue working on this database.

<!-- ### Scraping -->
<!-- The next step in the scraping pipeline would just be to schedule a cron job to scrape new urls every x hours, compare those to the list of already scraped urls, scrape the content of the new urls, and then run them through the same pre-processing and inference pipeline, so that the database is continually updated. -->

<!-- At some point, it would also be good to change the url scraper to run with [pyvirtualdisplay](https://github.com/ponty/PyVirtualDisplay) and [Xvfb](https://en.wikipedia.org/wiki/Xvfb) so it could be deployed in a headless environment[^2], and/or to find a third-party crawler service that works well with Above the Law. -->


[^1]: The outputs are kept separate so that each model could be independently evaluated.
<!-- [^2]: The selenium webdriver we use to scrape the urls can be run in a headless mode that does not require a display server, but headless operation can be easily detected by websites and anti-scraping measures are usually deployed in response. To get around this, we can create a fake graphical environment with Xvfb so that we look like a regular graphical user to the website. -->


import os
if 'Users' in os.getcwd(): #todo - unkludge
    root_path = '/Users/ben/Desktop/job/ner-takehome'
else:
    root_path = '/home/ben/ner-takehome'
os.chdir(root_path)


import re
from neo4j import GraphDatabase
from src.string_filters import is_name, has_bad_keyword


### LLAMA SERVER
# URI = "neo4j://10.249.64.7"
# AUTH = ("neo4j", "[big_secret]")

### FLAIR/BABEL SERVER
# URI = "neo4j://10.249.64.11"
# AUTH = ("neo4j", "[big_secret]")



class Neo4jDatabase():
    def __init__(self, URI: str, AUTH: str) -> None:
        self.driver =  GraphDatabase.driver(URI, auth=AUTH)
        self.driver.verify_connectivity()

    @staticmethod
    def generate_firm_list() -> list[dict]:
        firm_list = []
        with open(f'{root_dir}/data/scraped_firms.md', 'r') as f:
            data = f.readlines()
        for line in data:
            line = line.split('|')
            name = line[1]
            hq_location = line[2].strip()
            headcount = line[3].strip()
            if ']' in name:
                name_url = name.split(']')
                name = re.sub('[^a-zA-Z &-]', '',  name_url[0][1:].strip())
                url = name_url[1][1:-1].strip()
            else:
                url = ''
            print('-'*80)
            print('line is:', line)
            print('name is:', name)
            print('url is:', url)
            print('hq is:', hq_location)
            print('headcount is:', headcount)

            firm_list.append({'name':name, 'url':url, 'hq':hq_location, 'headcount':headcount})

        return firm_list


    def add_known_firms(self, firm_list: list) -> None:
        for firm in firm_list:
            records, summary, keys = self.driver.execute_query(
                """MERGE (:Firm {name: $name, url: $url, hq: $hq, headcount: $headcount})""",
                name = firm['name'],
                url = firm['url'],
                hq = firm['hq'],
                headcount = firm['headcount'],
                database_="neo4j",
            )
        return

    #translate 'Davis Polk' to 'Davis Polk & Wardwell' to avoid duplicates
    #TODO - consider doing same for employees; e.g. match 'William H. Aaronson' to 'William Aaronson' - BUT multiple people have the same name in a way that firms do not
    def check_firm_name(self, firm: str) -> str:
        known_firms = self.return_known_firm_names()
        results = [x for x in known_firms if ((x.lower() in firm.lower()) or (firm.lower() in x.lower()))]
        if len(results) != 0:
            firm = results[0]
            # if len(results) == 1:
            #     firm = results[0]
            # else:
            #     print('Error - ambiguous firm name! Not adding!')
            #     #raise ValueError
            #     return 'ERROR'
        return firm

    def is_known_firm(self, firm: str) -> str:
        known_firms = self.return_known_firm_names()
        results = [x for x in known_firms if ((x.lower() in firm.lower()) or (firm.lower() in x.lower()))]
        return (len(results) > 0)

    def add_employee(self, firm: str, employee: str) -> None:
        firm = self.check_firm_name(firm)
        if not(firm == 'ERROR'):
            self.driver.execute_query(
                """
                MERGE (ee:Person {name: $employee})
                MERGE (org:Firm {name: $firm})
                MERGE (org)-[:EMPLOYS]->(ee)
                MERGE (ee)-[:WORKS_FOR]->(org)
                """,
                firm=firm,
                employee=employee,
                database="neo4j"
            )
        return


    def add_employee_mention(self, employee: str, url: str, title: str) -> None:
        self.driver.execute_query(
            """
            MERGE (a:Article {title: $title, url: $url})
            MERGE (ee:Person {name: $employee})
            MERGE (ee)-[:MENTIONED_IN]->(a)
            MERGE (a)-[:MENTIONS]->(ee)
            """,
            title=title,
            url=url,
            employee=employee
        )

    def add_firm_mention(self, firm: str, url: str, title: str) -> None:
        firm = self.check_firm_name(firm)
        if not(firm == 'ERROR'):
            self.driver.execute_query(
                """
                MERGE (a:Article {title: $title, url: $url})
                MERGE (org:Firm {name: $firm})
                MERGE (org)-[:MENTIONED_IN]->(a)
                MERGE (a)-[:MENTIONS]->(org)
                """,
                title=title,
                url=url,
                firm=firm
            )

    def return_known_firm_names(self) -> list[str]:
        firms = self.driver.execute_query(
            """MATCH (n:Firm) RETURN n.name"""
        )
        return [x.value() for x in firms.records]



    def search_firm(self, firm: str) -> tuple[list[str], list[dict]]:
        firm = self.check_firm_name(firm)
        results = self.driver.execute_query(
            """
            MATCH (f:Firm WHERE f.name =~ $name)-[r]->(b)
            RETURN b
            """,
            name=firm
        )
        articles = []
        people = []
        for r in results.records:
            label = list(r.value()._labels)[0]
            if label == "Person":
                people.append(r.value()._properties['name'])
            elif label == 'Article':
                articles.append(r.value()._properties)

        people = list(set([x for x in people if (is_name(x) and not(has_bad_keyword(x)))]))
        people.sort()

        tmp_article_titles = []
        deduped_articles = []
        for article in articles:
            article['title'] = article['title'].split('- Above the Law')[0].strip()
            if not(article['title'] in tmp_article_titles):
                deduped_articles.append(article)
                tmp_article_titles.append(article['title'])
        return people, deduped_articles

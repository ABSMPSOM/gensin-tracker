import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import concurrent.futures


class GenshinQuestScraper:

    BASE_URL = "https://genshin-impact.fandom.com/"

    REGIONS = {

        "Inazuma": {
            "color": "purple",
            "element": "Electro",
            "bg": "from-purple-900/40"
        },

        "Sumeru": {
            "color": "green",
            "element": "Dendro",
            "bg": "from-green-900/40"
        },

        "Fontaine": {
            "color": "blue",
            "element": "Hydro",
            "bg": "from-blue-900/40"
        },

        "Natlan": {
            "color": "red",
            "element": "Pyro",
            "bg": "from-red-900/40"
        },

        "Liyue": {
            "color": "amber",
            "element": "Geo",
            "bg": "from-amber-900/40"
        },

        "Snezhnaya": {
            "color": "cyan",
            "element": "Cryo",
            "bg": "from-cyan-900/40"
        },

        "Mondstadt": {
            "color": "teal",
            "element": "Anemo",
            "bg": "from-teal-900/40"
        }
    }

    BLOCKED = [

        "other languages",
        "change history",
        "soundtracks",
        "gallery",
        "references",
        "navigation",
        "trivia",
        "characters"

    ]

    # ======================================================
    # IMAGE FIXER
    # ======================================================

    @staticmethod
    def get_high_res_image(url):

        if not url:
            return None

        url = (
            url
            .replace("/scale-to-width-down/120", "")
            .replace("/scale-to-width-down/250", "")
            .replace("/scale-to-width-down/300", "")
            .replace("/revision/latest", "")
        )

        return url

    # ======================================================
    # REGION DETECTOR
    # ======================================================

    def detect_region(self, text):

        text = text.lower()

        for region, data in self.REGIONS.items():

            if region.lower() in text:

                data["name"] = region
                return data

        return {

            "name": "Teyvat",
            "color": "yellow",
            "element": "Omni",
            "bg": "from-yellow-900/40"

        }

    # ======================================================
    # TIME ESTIMATION
    # ======================================================

    @staticmethod
    def estimate_metrics(step_text):

        text = step_text.lower()

        if any(
            word in text
            for word in [

                'defeat',
                'fight',
                'eliminate',
                'destroy',
                'protect'

            ]
        ):

            return {

                "time": 6,
                "type": "Combat",
                "color": "red"

            }

        elif any(
            word in text
            for word in [

                'go to',
                'travel',
                'follow',
                'reach',
                'head',
                'return'

            ]
        ):

            return {

                "time": 3,
                "type": "Exploration",
                "color": "blue"

            }

        elif any(
            word in text
            for word in [

                'investigate',
                'search',
                'collect',
                'solve'

            ]
        ):

            return {

                "time": 4,
                "type": "Puzzle",
                "color": "purple"

            }

        elif any(
            word in text
            for word in [

                'talk',
                'speak',
                'listen',
                'ask',
                'report'

            ]
        ):

            return {

                "time": 2,
                "type": "Dialogue",
                "color": "green"

            }

        return {

            "time": 2,
            "type": "Task",
            "color": "gray"

        }

    # ======================================================
    # FETCH PAGE
    # ======================================================

    def fetch_page_soup(self, query):

        api_url = (
            f"{self.BASE_URL}"
            f"api.php?action=parse"
            f"&page={quote(query)}"
            f"&format=json"
            f"&redirects=1"
        )

        try:

            response = requests.get(

                api_url,

                timeout=15,

                headers={
                    "User-Agent":
                    "Mozilla/5.0"
                }
            )

            if response.status_code == 200:

                data = response.json()

                if "parse" in data:

                    return (

                        BeautifulSoup(
                            data["parse"]["text"]["*"],
                            'html.parser'
                        ),

                        data["parse"]["title"]

                    )

        except Exception:
            pass

        return None, None

    # ======================================================
    # STEP EXTRACTION
    # ======================================================

    def extract_steps_and_time(self, soup):

        steps = []
        total_time = 0

        headings = [

            'steps',
            'objectives',
            'walkthrough',
            'dialogue',
            'quest walkthrough'

        ]

        target = None

        # ------------------------------------
        # FIND SECTION
        # ------------------------------------

        for span in soup.find_all(
            'span',
            class_='mw-headline'
        ):

            text = span.get_text(
                strip=True
            ).lower()

            if text in headings:

                target = span.parent
                break

        # ------------------------------------
        # PARSE TARGET
        # ------------------------------------

        if target:

            curr = target.find_next_sibling()

            while curr and curr.name not in ['h2', 'h3']:

                if curr.name in ['ol', 'ul']:

                    for li in curr.find_all(
                        'li',
                        recursive=False
                    ):

                        clean = re.sub(
                            r'\[\d+\]',
                            '',
                            li.get_text(
                                separator=" ",
                                strip=True
                            )
                        )

                        clean = clean.split(
                            '\n'
                        )[0].strip()

                        if (
                            len(clean) > 5
                            and len(clean) < 160
                        ):

                            if any(
                                b in clean.lower()
                                for b in self.BLOCKED
                            ):
                                continue

                            metrics = self.estimate_metrics(
                                clean
                            )

                            total_time += metrics['time']

                            steps.append({

                                "text": clean,

                                "type":
                                metrics['type'],

                                "color":
                                metrics['color'],

                                "est_time":
                                metrics['time']

                            })

                curr = curr.find_next_sibling()

        # ------------------------------------
        # FALLBACK
        # ------------------------------------

        if not steps:

            for ol in soup.find_all(['ol', 'ul']):

                items = ol.find_all(
                    'li',
                    recursive=False
                )

                if len(items) >= 3:

                    for li in items[:8]:

                        clean = re.sub(
                            r'\[\d+\]',
                            '',
                            li.get_text(
                                separator=" ",
                                strip=True
                            )
                        )

                        clean = clean.strip()

                        if (
                            len(clean) > 5
                            and len(clean) < 150
                        ):

                            metrics = self.estimate_metrics(
                                clean
                            )

                            total_time += metrics['time']

                            steps.append({

                                "text": clean,

                                "type":
                                metrics['type'],

                                "color":
                                metrics['color'],

                                "est_time":
                                metrics['time']

                            })

                    if steps:
                        break

        return steps[:8], total_time

    # ======================================================
    # REWARD EXTRACTION
    # ======================================================

    def extract_rewards(self, soup):

        text = soup.get_text(" ")

        match = re.search(

            r'(\d+)\s*(?:x|×)?\s*Primogem',

            text,

            re.IGNORECASE
        )

        if match:

            return int(match.group(1))

        lower = text.lower()

        if "archon quest" in lower:
            return 60

        if "story quest" in lower:
            return 60

        if "world quest" in lower:
            return 40

        return 30

    # ======================================================
    # PROCESS SUBQUEST
    # ======================================================

    def process_subquest(self, sq_name):

        soup, _ = self.fetch_page_soup(
            sq_name
        )

        if not soup:
            return None

        steps, total_time = (
            self.extract_steps_and_time(
                soup
            )
        )

        rewards = self.extract_rewards(
            soup
        )

        if not steps:
            return None

        return {

            "name": sq_name,

            "steps": steps,

            "est_time": total_time,

            "primos": rewards

        }

    # ======================================================
    # MAIN PARSER
    # ======================================================

    def fetch_quest_data(self, query):

        soup, title = self.fetch_page_soup(
            query.strip()
        )

        if not soup:

            return {

                "error":
                f"Quest '{query}' not found."

            }

        try:

            # --------------------------------
            # BANNER
            # --------------------------------

            banner = None

            selectors = [

                ".pi-image-thumbnail",
                ".infobox-image img",
                "figure a.image img",
                ".wds-tab__content img",
                ".image img",
                "aside img"

            ]

            for selector in selectors:

                img = soup.select_one(
                    selector
                )

                if img:

                    src = (
                        img.get('data-src')
                        or img.get('src')
                    )

                    if src:

                        bad = [

                            "icon",
                            ".gif",
                            "sprite",
                            "loading"

                        ]

                        if not any(
                            b in src.lower()
                            for b in bad
                        ):

                            banner = (
                                self
                                .get_high_res_image(
                                    src
                                )
                            )

                            break

            # --------------------------------
            # DESCRIPTION
            # --------------------------------

            description = ""

            for p in soup.find_all('p'):

                text = p.get_text(
                    strip=True
                )

                if (
                    len(text) > 50
                    and not p.find_parent('aside')
                ):

                    description = re.sub(
                        r'\[\d+\]',
                        '',
                        text
                    )

                    break

            region = self.detect_region(
                title + " " + description
            )

            # --------------------------------
            # SUBQUESTS
            # --------------------------------

            subquest_links = []

            for span in soup.find_all(
                'span',
                class_='mw-headline'
            ):

                heading = span.get_text(
                    strip=True
                ).lower()

                if heading in [

                    'quests',
                    'quest chain',
                    'subquests',
                    'list of quests',
                    'walkthrough',
                    'steps'

                ]:

                    curr = (
                        span.parent
                        .find_next_sibling()
                    )

                    while curr and curr.name not in ['h2', 'h3']:

                        if curr.name in ['ol', 'ul']:

                            for li in curr.find_all('li'):

                                a = li.find('a')

                                if (
                                    a
                                    and a.has_attr('title')
                                ):

                                    title_name = (
                                        a['title']
                                    )

                                    if title_name not in subquest_links:

                                        subquest_links.append(
                                            title_name
                                        )

                        curr = curr.find_next_sibling()

            # --------------------------------
            # CHAPTER PARSING
            # --------------------------------

            subquests = []

            total_time = 0
            total_rewards = 0
            total_steps = 0

            is_chapter = (
                len(subquest_links) > 0
            )

            if is_chapter:

                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=5
                ) as executor:

                    results = list(

                        executor.map(
                            self.process_subquest,
                            subquest_links[:6]
                        )
                    )

                for res in results:

                    if res:

                        subquests.append(res)

                        total_time += (
                            res['est_time']
                        )

                        total_rewards += (
                            res['primos']
                        )

                        total_steps += len(
                            res['steps']
                        )

            else:

                main_steps, total_time = (
                    self.extract_steps_and_time(
                        soup
                    )
                )

                total_rewards = (
                    self.extract_rewards(
                        soup
                    )
                )

                total_steps = len(
                    main_steps
                )

            return {

                "title": title,

                "description": description,

                "banner_url": banner,

                "region": region,

                "is_chapter": is_chapter,

                "main_steps":
                [] if is_chapter
                else main_steps,

                "subquests": subquests,

                "stats": {

                    "estimated_time":

                    f"{total_time // 60}h "
                    f"{total_time % 60}m"

                    if total_time >= 60
                    else f"{total_time} Mins",

                    "total_steps":
                    total_steps,

                    "primos":
                    total_rewards

                }
            }

        except Exception as e:

            return {

                "error":
                f"System Error: {str(e)}"

            }
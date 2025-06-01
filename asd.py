# management/commands/fetch_fkko.py

import csv
import requests
from bs4 import BeautifulSoup

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Скачивает весь каталог ФККО и сохраняет в data/fkko.csv"

    BASE = "https://rpn.gov.ru/fkko/"

    def handle(self, *args, **options):
        url = self.BASE
        rows = []

        # на главной странице пагинации может не быть — тут пример для первой страницы
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # собираем ссылки на все подстраницы (по первой букве или цифре кода)
        nav = soup.select_one(".pagination-selector")  # пример селектора — уточните в HTML
        links = {url}
        if nav:
            for a in nav.select("a"):
                href = a.get("href")
                if href:
                    links.add(requests.compat.urljoin(self.BASE, href))

        for page in links:
            r = requests.get(page, timeout=10)
            r.raise_for_status()
            sp = BeautifulSoup(r.text, "html.parser")
            for row in sp.select(".registryCard__itemTableRow"):
                if "_head" in (row.get("class") or []):
                    continue
                code = row.select_one(".registryCard__itemTableCol._code").get_text(strip=True)
                name = row.select_one(".registryCard__itemTableCol._name a").get_text(strip=True)
                rows.append((code, name))

        # сохраняем в CSV
        with open("data/fkko.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(("code", "name"))
            writer.writerows(rows)

        self.stdout.write(self.style.SUCCESS(f"Сохранено {len(rows)} записей в data/fkko.csv"))
